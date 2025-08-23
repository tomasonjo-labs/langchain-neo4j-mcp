# Neo4j Vector GraphRAG MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to perform semantic search across Neo4j knowledge graphs using vector similarity and graph traversal.

## What it does

This server combines vector embeddings with graph database capabilities:
- Converts natural language queries to vector embeddings
- Searches Neo4j vector indexes for semantically similar content
- Uses custom Cypher queries to traverse the graph for additional context
- Returns enriched results combining semantic relevance with graph relationships

## Claude Desktop Configuration

Add to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "neo4j-vector": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/servers/mcp-neo4j-vector-graphrag",
        "run", "mcp-neo4j-vector-graphrag"
      ],
      "env": {
        "NEO4J_URI": "neo4j+s://demo.neo4jlabs.com:7687",
        "NEO4J_USERNAME": "recommendations",
        "NEO4J_PASSWORD": "recommendations",
        "NEO4J_DATABASE": "recommendations",
        "OPENAI_API_KEY": "sk-proj-your-key",
        "INDEX_NAME": "moviePlotsEmbedding",
        "EMBEDDING_MODEL": "openai:text-embedding-ada-002",
        "RETRIEVAL_QUERY": "RETURN 'Title: ' + coalesce(node.title,'') + 'Plot: ' + coalesce(node.plot, '') AS text, {imdbRating: node.imdbRating} AS metadata, score"
      }
    }
  }
}
```

Once configured, you can ask Claude natural language questions about your graph data:

- "Find movies about space exploration"
- "What documents mention artificial intelligence?"
- "Search for research papers on climate change"

Claude will use the vector search tool to find semantically relevant content from your Neo4j knowledge graph.

## Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `NEO4J_URI` | Neo4j database connection URI | ✓ | `neo4j+s://demo.neo4jlabs.com:7687` |
| `NEO4J_USERNAME` | Database username | ✓ | `neo4j` |
| `NEO4J_PASSWORD` | Database password | ✓ | `password` |
| `INDEX_NAME` | Vector index name to search | ✓ | `moviePlotsEmbedding` |
| `EMBEDDING_MODEL` | Embedding model to use | ✓ | `openai:text-embedding-ada-002` |
| `RETRIEVAL_QUERY` | Cypher query for result formatting | ✓ | `RETURN node.text AS text, score` |
| `NEO4J_DATABASE` | Target database name | | `neo4j` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI models) | * | `sk-proj-...` |

*Required only when using OpenAI embedding models

