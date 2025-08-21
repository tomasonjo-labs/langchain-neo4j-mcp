import argparse
import asyncio

from . import server
from .utils import process_config


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="Neo4j Vector MCP Server")
    parser.add_argument("--db-url", default=None, help="Neo4j connection URL")
    parser.add_argument("--username", default=None, help="Neo4j username")
    parser.add_argument("--password", default=None, help="Neo4j password")
    parser.add_argument("--database", default=None, help="Neo4j database name")
    parser.add_argument("--index-name", default=None, help="Neo4j vector index name")
    parser.add_argument("--embedding-model", default=None, help="Embedding model to use")
    parser.add_argument("--keyword-index-name", default=None, help="Neo4j keyword index name for hybrid search")
    parser.add_argument("--retrieval-query", default=None, help="Custom retrieval query")
    parser.add_argument(
        "--transport", default=None, help="Transport type (stdio, sse, http)"
    )
    parser.add_argument("--namespace", default=None, help="Tool namespace")
    parser.add_argument(
        "--server-path", default=None, help="HTTP path (default: /mcp/)"
    )
    parser.add_argument("--server-host", default=None, help="Server host")
    parser.add_argument("--server-port", default=None, help="Server port")

    args = parser.parse_args()
    config = process_config(args)
    asyncio.run(server.main(**config))


__all__ = ["main", "server"]