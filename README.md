# langchain-neo4j-mcp

## Example usage

```
{
  "mcpServers": {
    "neo4j-dev": {
      "command": "uv",
      "args": ["--directory", "path/to/langchain-neo4j-mcp/servers/mcp-neo4j-vector", "run", "mcp-neo4j-vector", "--transport", "stdio", "--namespace", "dev"],
      "env": {
        "NEO4J_URI": "neo4j+s://demo.neo4jlabs.com:7687",
        "NEO4J_USERNAME": "recommendations",
        "NEO4J_PASSWORD": "recommendations",
        "NEO4J_DATABASE": "recommendations",
        "OPENAI_API_KEY": "sk-proj-",
        "INDEX_NAME": "moviePlotsEmbedding",
        "KEYWORD_INDEX_NAME": "movieFulltext",
        "EMBEDDING_MODEL": "openai:text-embedding-ada-002",
        "RETRIEVAL_QUERY": "RETURN 'Title: ' + node.title + 'Plot: ' + node.plot AS text, {imdbRating: node.imdbRating} AS metadata, score"
      }
    }
  }
}
```