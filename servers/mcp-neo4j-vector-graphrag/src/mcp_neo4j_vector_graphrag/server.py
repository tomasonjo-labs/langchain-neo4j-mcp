import logging
from typing import Literal

from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from fastmcp.tools.tool import TextContent, ToolResult
from mcp.types import ToolAnnotations
from neo4j.exceptions import Neo4jError
from neo4j import GraphDatabase
from pydantic import Field

from neo4j_graphrag.retrievers import VectorCypherRetriever
from langchain.embeddings import init_embeddings

logger = logging.getLogger("mcp_neo4j_vector_graphrag")

def _format_namespace(namespace: str) -> str:
    if namespace:
        if namespace.endswith("-"):
            return namespace
        else:
            return namespace + "-"
    else:
        return ""

def create_mcp_server(
    vector_retriever: VectorCypherRetriever, namespace: str = ""
) -> FastMCP:
    mcp: FastMCP = FastMCP(
        "mcp-neo4j-vector-graphrag", dependencies=["neo4j-graphrag", "pydantic"], stateless_http=True
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
    async def vector_search(
        query: str = Field(..., description="Natural language question to search for.")
    ) -> list[ToolResult]:
        """Find relevant documents based on natural language input"""

        try:

            result = vector_retriever.search(query_text=query, top_k=5)
            text = "\n".join(item.content for item in result.items)

            return ToolResult(content=[TextContent(type="text", text=text)])

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
    index_name: str,
    embedding_model: str,
    keyword_index_name: str,
    retrieval_query: str,
    transport: Literal["stdio", "sse", "http"] = "stdio",
    namespace: str = "",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp/",
) -> None:
    logger.info("Starting MCP neo4j Server")

    embedding_model = init_embeddings(embedding_model)
    driver = GraphDatabase.driver(db_url, auth=(username, password))
    retriever = VectorCypherRetriever(
        driver,
        index_name=index_name,
        embedder=embedding_model,
        retrieval_query=retrieval_query,
        neo4j_database=database
    )

    mcp = create_mcp_server(retriever, namespace)

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
