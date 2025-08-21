import logging
from typing import Any, Literal

from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from fastmcp.tools.tool import TextContent, ToolResult
from mcp.types import ToolAnnotations
from neo4j.exceptions import Neo4jError
from pydantic import Field
from langchain_openai import OpenAIEmbeddings

from langchain_neo4j import Neo4jVector

logger = logging.getLogger("mcp_neo4j_vector")

def format_as_xml(data, query):
    if not data:
        return "<results>No relevant documents found.</results>"
    
    xml_parts = [f"<query>{query}</query>", "<results>"]
    
    for i, doc in enumerate(data):
        xml_parts.append(f"<document id='{i+1}'>")
        xml_parts.append(f"<content>{doc.page_content}</content>")
        if doc.metadata:
            xml_parts.append("<metadata>")
            for key, value in doc.metadata.items():
                xml_parts.append(f"<{key}>{value}</{key}>")
            xml_parts.append("</metadata>")
        xml_parts.append("</document>")
    
    xml_parts.append("</results>")
    return "\n".join(xml_parts)

def _format_namespace(namespace: str) -> str:
    if namespace:
        if namespace.endswith("-"):
            return namespace
        else:
            return namespace + "-"
    else:
        return ""

def create_mcp_server(
    vector_store: Neo4jVector, namespace: str = ""
) -> FastMCP:
    mcp: FastMCP = FastMCP(
        "mcp-neo4j-vector", dependencies=["langchain-neo4j", "pydantic"], stateless_http=True
    )

    namespace_prefix = _format_namespace(namespace)

    @mcp.tool(
        name=namespace_prefix + "neo4j_vector",
        annotations=ToolAnnotations(
            title="Neo4j vector",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def find_movies(
        query: str = Field(..., description="Natural language question to find a movie.")
    ) -> list[ToolResult]:
        """Find movies based on natural language input"""

        try:

            data = vector_store.similarity_search(query)
            logger.debug(f"Read query returned {len(data)} rows")

            return ToolResult(content=[TextContent(type="text", text=format_as_xml(data, query))])

        except Neo4jError as e:
            logger.error(f"Neo4j Error executing read query: {e}\n{query}")
            raise ToolError(f"Neo4j Error: {e}\n{query}")

        except Exception as e:
            logger.error(f"Error executing read query: {e}\n{query}")
            raise ToolError(f"Error: {e}\n{query}")
        
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
) -> None:
    logger.info("Starting MCP neo4j Server")

    neo4j_vector_store = Neo4jVector.from_existing_index(
        OpenAIEmbeddings(model='text-embedding-ada-002'),
        url=db_url,
        username=username,
        password=password,
        database=database,
        index_name="moviePlotsEmbedding",
        keyword_index_name="movieFulltext",
        search_type="hybrid"
    )

    mcp = create_mcp_server(neo4j_vector_store, namespace)

    # Run the server with the specified transport
    match transport:
        case "http":
            logger.info(
                f"Running Neo4j Vector MCP Server with HTTP transport on {host}:{port}..."
            )
            await mcp.run_http_async(host=host, port=port, path=path)
        case "stdio":
            logger.info("Running Neo4j Vector MCP Server with stdio transport...")
            await mcp.run_stdio_async()
        case "sse":
            logger.info(
                f"Running Neo4j Vector MCP Server with SSE transport on {host}:{port}..."
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
