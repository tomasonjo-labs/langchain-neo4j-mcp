import argparse
import logging
import os
from typing import Union

logger = logging.getLogger("mcp_neo4j_cypher")
logger.setLevel(logging.INFO)


def process_config(args: argparse.Namespace) -> dict[str, Union[str, int, None]]:
    """
    Process the command line arguments and environment variables to create a config dictionary.
    This may then be used as input to the main server function.
    If any value is not provided, then a warning is logged and a default value is used, if appropriate.

    Parameters
    ----------
    args : argparse.Namespace
        The command line arguments.

    Returns
    -------
    config : dict[str, str]
        The configuration dictionary.
    """

    config = dict()

    # parse uri
    if args.db_url is not None:
        config["db_url"] = args.db_url
    else:
        if os.getenv("NEO4J_URL") is not None:
            config["db_url"] = os.getenv("NEO4J_URL")
        else:
            if os.getenv("NEO4J_URI") is not None:
                config["db_url"] = os.getenv("NEO4J_URI")
            else:
                logger.warning(
                    "Warning: No Neo4j connection URL provided. Using default: bolt://localhost:7687"
                )
                config["db_url"] = "bolt://localhost:7687"

    # parse username
    if args.username is not None:
        config["username"] = args.username
    else:
        if os.getenv("NEO4J_USERNAME") is not None:
            config["username"] = os.getenv("NEO4J_USERNAME")
        else:
            logger.warning("Warning: No Neo4j username provided. Using default: neo4j")
            config["username"] = "neo4j"

    # parse password
    if args.password is not None:
        config["password"] = args.password
    else:
        if os.getenv("NEO4J_PASSWORD") is not None:
            config["password"] = os.getenv("NEO4J_PASSWORD")
        else:
            logger.warning(
                "Warning: No Neo4j password provided. Using default: password"
            )
            config["password"] = "password"

    # parse database
    if args.database is not None:
        config["database"] = args.database
    else:
        if os.getenv("NEO4J_DATABASE") is not None:
            config["database"] = os.getenv("NEO4J_DATABASE")
        else:
            logger.warning("Warning: No Neo4j database provided. Using default: neo4j")
            config["database"] = "neo4j"

    # parse namespace
    if args.namespace is not None:
        config["namespace"] = args.namespace
    else:
        if os.getenv("NEO4J_NAMESPACE") is not None:
            config["namespace"] = os.getenv("NEO4J_NAMESPACE")
        else:
            logger.info("Info: No namespace provided. No namespace will be used.")
            config["namespace"] = ""

    # parse transport
    if args.transport is not None:
        config["transport"] = args.transport
    else:
        if os.getenv("NEO4J_TRANSPORT") is not None:
            config["transport"] = os.getenv("NEO4J_TRANSPORT")
        else:
            logger.warning("Warning: No transport type provided. Using default: stdio")
            config["transport"] = "stdio"

    # parse server host
    if args.server_host is not None:
        if config["transport"] == "stdio":
            logger.warning(
                "Warning: Server host provided, but transport is `stdio`. The `server_host` argument will be set, but ignored."
            )
        config["host"] = args.server_host
    else:
        if os.getenv("NEO4J_MCP_SERVER_HOST") is not None:
            if config["transport"] == "stdio":
                logger.warning(
                    "Warning: Server host provided, but transport is `stdio`. The `NEO4J_MCP_SERVER_HOST` environment variable will be set, but ignored."
                )
            config["host"] = os.getenv("NEO4J_MCP_SERVER_HOST")
        elif config["transport"] != "stdio":
            logger.warning(
                "Warning: No server host provided and transport is not `stdio`. Using default server host: 127.0.0.1"
            )
            config["host"] = "127.0.0.1"
        else:
            logger.info(
                "Info: No server host provided and transport is `stdio`. `server_host` will be None."
            )
            config["host"] = None

    # parse server port
    if args.server_port is not None:
        if config["transport"] == "stdio":
            logger.warning(
                "Warning: Server port provided, but transport is `stdio`. The `server_port` argument will be set, but ignored."
            )
        config["port"] = args.server_port
    else:
        if os.getenv("NEO4J_MCP_SERVER_PORT") is not None:
            if config["transport"] == "stdio":
                logger.warning(
                    "Warning: Server port provided, but transport is `stdio`. The `NEO4J_MCP_SERVER_PORT` environment variable will be set, but ignored."
                )
            config["port"] = int(os.getenv("NEO4J_MCP_SERVER_PORT"))
        elif config["transport"] != "stdio":
            logger.warning(
                "Warning: No server port provided and transport is not `stdio`. Using default server port: 8000"
            )
            config["port"] = 8000
        else:
            logger.info(
                "Info: No server port provided and transport is `stdio`. `server_port` will be None."
            )
            config["port"] = None

    # parse server path
    if args.server_path is not None:
        if config["transport"] == "stdio":
            logger.warning(
                "Warning: Server path provided, but transport is `stdio`. The `server_path` argument will be set, but ignored."
            )
        config["path"] = args.server_path
    else:
        if os.getenv("NEO4J_MCP_SERVER_PATH") is not None:
            if config["transport"] == "stdio":
                logger.warning(
                    "Warning: Server path provided, but transport is `stdio`. The `NEO4J_MCP_SERVER_PATH` environment variable will be set, but ignored."
                )
            config["path"] = os.getenv("NEO4J_MCP_SERVER_PATH")
        elif config["transport"] != "stdio":
            logger.warning(
                "Warning: No server path provided and transport is not `stdio`. Using default server path: /mcp/"
            )
            config["path"] = "/mcp/"
        else:
            logger.info(
                "Info: No server path provided and transport is `stdio`. `server_path` will be None."
            )
            config["path"] = None

    return config
