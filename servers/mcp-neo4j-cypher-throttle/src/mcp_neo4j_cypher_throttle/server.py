import json
import logging
import os
import re
from typing import Any, Literal

import tiktoken

from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from fastmcp.tools.tool import TextContent, ToolResult
from mcp.types import ToolAnnotations
from neo4j import AsyncDriver, AsyncGraphDatabase, RoutingControl, Query
from neo4j.exceptions import ClientError, Neo4jError
from pydantic import Field

logger = logging.getLogger("mcp_neo4j_cypher_throttle")

def _truncate_string_to_tokens(text: str, token_limit: int = 2048, model: str = "gpt-4") -> str:
    """
    Truncates the input string to fit within the specified token limit.
    
    Args:
        text (str): The input text string.
        token_limit (int): Maximum number of tokens allowed. Defaults to 2048.
        model (str): Model name (affects tokenization). Defaults to "gpt-4".
    
    Returns:
        str: The truncated string that fits within the token limit.
    """
    # Load encoding for the chosen model
    encoding = tiktoken.encoding_for_model(model)

    # Encode text into tokens
    tokens = encoding.encode(text)

    # Truncate tokens if they exceed the limit
    if len(tokens) > token_limit:
        tokens = tokens[:token_limit]

    # Decode back into text
    truncated_text = encoding.decode(tokens)
    return truncated_text

def _value_sanitize(d: Any, list_limit: int = 52) -> Any:
    """Sanitize the input dictionary or list.

    Sanitizes the input by removing embedding-like values,
    lists with more than 128 elements, that are mostly irrelevant for
    generating answers in a LLM context. These properties, if left in
    results, can occupy significant context space and detract from
    the LLM's performance by introducing unnecessary noise and cost.

    Args:
        d (Any): The input dictionary or list to sanitize.

    Returns:
        Any: The sanitized dictionary or list.
    """
    if isinstance(d, dict):
        new_dict = {}
        for key, value in d.items():
            if isinstance(value, dict):
                sanitized_value = _value_sanitize(value)
                if (
                    sanitized_value is not None
                ):  # Check if the sanitized value is not None
                    new_dict[key] = sanitized_value
            elif isinstance(value, list):
                if len(value) < list_limit:
                    sanitized_value = _value_sanitize(value)
                    if (
                        sanitized_value is not None
                    ):  # Check if the sanitized value is not None
                        new_dict[key] = sanitized_value
                # Do not include the key if the list is oversized
            else:
                new_dict[key] = value
        return new_dict
    elif isinstance(d, list):
        if len(d) < list_limit:
            return [
                _value_sanitize(item) for item in d if _value_sanitize(item) is not None
            ]
        else:
            return None
    else:
        return d



def _format_namespace(namespace: str) -> str:
    if namespace:
        if namespace.endswith("-"):
            return namespace
        else:
            return namespace + "-"
    else:
        return ""


def _is_write_query(query: str) -> bool:
    """Check if the query is a write query."""
    return (
        re.search(r"\b(MERGE|CREATE|SET|DELETE|REMOVE|ADD)\b", query, re.IGNORECASE)
        is not None
    )

def create_mcp_server(
    neo4j_driver: AsyncDriver, database: str = "neo4j", namespace: str = "", query_timeout: float = 10.0
) -> FastMCP:
    mcp: FastMCP = FastMCP(
        "mcp-neo4j-cypher-throttle", dependencies=["neo4j", "pydantic", "tiktoken"], stateless_http=True
    )

    namespace_prefix = _format_namespace(namespace)

    @mcp.tool(
        name=namespace_prefix + "get_neo4j_schema",
        annotations=ToolAnnotations(
            title="Get Neo4j Schema",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def get_neo4j_schema() -> list[ToolResult]:
        """
        List all nodes, their attributes and their relationships to other nodes in the neo4j database.
        This requires that the APOC plugin is installed and enabled.
        """

        get_schema_query = """
        CALL apoc.meta.schema();
        """

        def clean_schema(schema: dict) -> dict:
            cleaned = {}

            for key, entry in schema.items():
                new_entry = {"type": entry["type"]}
                if "count" in entry:
                    new_entry["count"] = entry["count"]

                labels = entry.get("labels", [])
                if labels:
                    new_entry["labels"] = labels

                props = entry.get("properties", {})
                clean_props = {}
                for pname, pinfo in props.items():
                    cp = {}
                    if "indexed" in pinfo:
                        cp["indexed"] = pinfo["indexed"]
                    if "type" in pinfo:
                        cp["type"] = pinfo["type"]
                    if cp:
                        clean_props[pname] = cp
                if clean_props:
                    new_entry["properties"] = clean_props

                if entry.get("relationships"):
                    rels_out = {}
                    for rel_name, rel in entry["relationships"].items():
                        cr = {}
                        if "direction" in rel:
                            cr["direction"] = rel["direction"]
                        # nested labels
                        rlabels = rel.get("labels", [])
                        if rlabels:
                            cr["labels"] = rlabels
                        # nested properties
                        rprops = rel.get("properties", {})
                        clean_rprops = {}
                        for rpname, rpinfo in rprops.items():
                            crp = {}
                            if "indexed" in rpinfo:
                                crp["indexed"] = rpinfo["indexed"]
                            if "type" in rpinfo:
                                crp["type"] = rpinfo["type"]
                            if crp:
                                clean_rprops[rpname] = crp
                        if clean_rprops:
                            cr["properties"] = clean_rprops

                        if cr:
                            rels_out[rel_name] = cr

                    if rels_out:
                        new_entry["relationships"] = rels_out

                cleaned[key] = new_entry

            return cleaned

        try:
            results_json_str = await neo4j_driver.execute_query(
                get_schema_query,
                routing_control=RoutingControl.READ,
                database_=database,
                result_transformer_=lambda r: r.data(),
            )

            logger.debug(f"Read query returned {len(results_json_str)} rows")

            schema_clean = clean_schema(results_json_str[0].get("value"))

            schema_clean_str = json.dumps(schema_clean, default=str)

            return ToolResult(content=[TextContent(type="text", text=schema_clean_str)])

        except ClientError as e:
            if "Neo.ClientError.Procedure.ProcedureNotFound" in str(e):
                raise ToolError(
                    "Neo4j Client Error: This instance of Neo4j does not have the APOC plugin installed. Please install and enable the APOC plugin to use the `get_neo4j_schema` tool."
                )
            else:
                raise ToolError(f"Neo4j Client Error: {e}")

        except Neo4jError as e:
            raise ToolError(f"Neo4j Error: {e}")

        except Exception as e:
            logger.error(f"Error retrieving Neo4j database schema: {e}")
            raise ToolError(f"Unexpected Error: {e}")

    @mcp.tool(
        name=namespace_prefix + "read_neo4j_cypher",
        annotations=ToolAnnotations(
            title="Read Neo4j Cypher",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def read_neo4j_cypher(
        query: str = Field(..., description="The Cypher query to execute."),
        params: dict[str, Any] = Field(
            dict(), description="The parameters to pass to the Cypher query."
        ),
    ) -> list[ToolResult]:
        """Execute a read Cypher query on the neo4j database."""

        if _is_write_query(query):
            raise ValueError("Only MATCH queries are allowed for read-query")

        try:
            results = await neo4j_driver.execute_query(
                Query(query, timeout=query_timeout),
                parameters_=params,
                routing_control=RoutingControl.READ,
                database_=database,
                result_transformer_=lambda r: r.data(),
            )

            results_json_str = json.dumps([_value_sanitize(el) for el in results], default=str)
            truncated_results = _truncate_string_to_tokens(results_json_str)

            logger.debug(f"Read query returned {len(results_json_str)} rows")

            return ToolResult(content=[TextContent(type="text", text=truncated_results)])

        except Neo4jError as e:
            logger.error(f"Neo4j Error executing read query: {e}\n{query}\n{params}")
            raise ToolError(f"Neo4j Error: {e}\n{query}\n{params}")

        except Exception as e:
            logger.error(f"Error executing read query: {e}\n{query}\n{params}")
            raise ToolError(f"Error: {e}\n{query}\n{params}")

    @mcp.tool(
        name=namespace_prefix + "write_neo4j_cypher",
        annotations=ToolAnnotations(
            title="Write Neo4j Cypher",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def write_neo4j_cypher(
        query: str = Field(..., description="The Cypher query to execute."),
        params: dict[str, Any] = Field(
            dict(), description="The parameters to pass to the Cypher query."
        ),
    ) -> list[ToolResult]:
        """Execute a write Cypher query on the neo4j database."""

        if not _is_write_query(query):
            raise ValueError("Only write queries are allowed for write-query")

        try:
            _, summary, _ = await neo4j_driver.execute_query(
                Query(query, timeout=query_timeout),
                parameters_=params,
                routing_control=RoutingControl.WRITE,
                database_=database,
            )

            counters_json_str = json.dumps(summary.counters.__dict__, default=str)

            logger.debug(f"Write query affected {counters_json_str}")

            return ToolResult(
                content=[TextContent(type="text", text=counters_json_str)]
            )

        except Neo4jError as e:
            logger.error(f"Neo4j Error executing write query: {e}\n{query}\n{params}")
            raise ToolError(f"Neo4j Error: {e}\n{query}\n{params}")

        except Exception as e:
            logger.error(f"Error executing write query: {e}\n{query}\n{params}")
            raise ToolError(f"Error: {e}\n{query}\n{params}")

    return mcp


async def main(
    db_url: str,
    username: str,
    password: str,
    database: str,
    transport: Literal["stdio", "sse", "http"] = "stdio",
    namespace: str = "",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp/",
    query_timeout: float = 10.0
) -> None:
    logger.info("Starting MCP neo4j Server")

    neo4j_driver = AsyncGraphDatabase.driver(
        db_url,
        auth=(
            username,
            password,
        ),
    )

    mcp = create_mcp_server(neo4j_driver, database, namespace, query_timeout)

    # Run the server with the specified transport
    match transport:
        case "http":
            logger.info(
                f"Running Neo4j Cypher MCP Server with HTTP transport on {host}:{port}..."
            )
            await mcp.run_http_async(host=host, port=port, path=path)
        case "stdio":
            logger.info("Running Neo4j Cypher MCP Server with stdio transport...")
            await mcp.run_stdio_async()
        case "sse":
            logger.info(
                f"Running Neo4j Cypher MCP Server with SSE transport on {host}:{port}..."
            )
            await mcp.run_sse_async(host=host, port=port, path=path)
        case _:
            logger.error(
                f"Invalid transport: {transport} | Must be either 'stdio', 'sse', or 'http'"
            )
            raise ValueError(
                f"Invalid transport: {transport} | Must be either 'stdio', 'sse', or 'http'"
            )


if __name__ == "__main__":
    main()