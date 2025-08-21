import json
from typing import Any

import pytest
from fastmcp.server import FastMCP


@pytest.mark.asyncio(loop_scope="function")
async def test_get_neo4j_schema(mcp_server: FastMCP, init_data: Any):
    tool = await mcp_server.get_tool("get_neo4j_schema")
    response = await tool.run(dict())

    schema = json.loads(response.content[0].text)

    # Verify the schema result
    assert "Person" in schema
    assert schema["Person"]["count"] == 3
    assert len(schema["Person"]["properties"]) == 2
    assert "FRIEND" in schema["Person"]["relationships"]


@pytest.mark.asyncio(loop_scope="function")
async def test_write_neo4j_cypher(mcp_server: FastMCP):
    query = "CREATE (n:Test {name: 'test', age: 123}) RETURN n.name"
    tool = await mcp_server.get_tool("write_neo4j_cypher")
    response = await tool.run(dict(query=query))

    result = json.loads(response.content[0].text)

    assert "nodes_created" in result
    assert "labels_added" in result
    assert "properties_set" in result
    assert result["nodes_created"] == 1
    assert result["labels_added"] == 1
    assert result["properties_set"] == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_read_neo4j_cypher(mcp_server: FastMCP, init_data: Any):
    query = """
    MATCH (p:Person)-[:FRIEND]->(friend)
    RETURN p.name AS person, friend.name AS friend_name
    ORDER BY p.name, friend.name
    """

    tool = await mcp_server.get_tool("read_neo4j_cypher")
    response = await tool.run(dict(query=query))

    result = json.loads(response.content[0].text)

    assert len(result) == 2
    assert result[0]["person"] == "Alice"
    assert result[0]["friend_name"] == "Bob"
    assert result[1]["person"] == "Bob"
    assert result[1]["friend_name"] == "Charlie"
