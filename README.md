#  MCP Server for ProKN

This folder contains the code for an MCP server for ProKN. It is built using FastMCP with foundational tools required to enable the usecases at https://research.bioinformatics.udel.edu/ProKN/usecases.  

## Index:
- [Local Development](#local-development)
- [Build Docker Image](#build-docker-image)
- [Deploying to ProKN Server](#deploying-to-prokn-server)
- [Usage](#usage)
- [Evaluation](#evaluation)
- [Some Observations](#some-observations)
- [TODOs / Discussion Items](#todos--discussion-items)

## Local Development

### Requirements
- Python 3.10+
- An MCP Client (e.g. Google Antigravity or Claude Desktop)
- FastMCP - `pip install -r requirements.txt`
- (Optional) if using the stdio transport: `uv` python package manager. See https://docs.astral.sh/uv/getting-started/installation/ for installation instructions

### Procedure
To run the FastMCP Server in a local terminal session for development:
1. Port forward the Neo4j instance running on the remote server to a port on your local machine. E.g.
```sh
ssh -N -L <neo4j_local_port>:localhost:<neo4j_remote_port> <username>@<hostname>
```
2. In a new terminal session, export the following environment variables:

```bash
export NEO4J_URI="bolt://localhost:<neo4j_local_port>"
export NEO4J_USERNAME="<neo4j_username>" #(usually neo4j)
export NEO4J_PASSWORD="<neo4j_password>"
```
3. Start the MCP Server: `python tools/mcpserver/mcpserver.py sse`
4. Add the following config to your MCP Client's MCP server list. If the `mcpservers` key already exists, then just add the `prokn-mcp-server` key and value under it. 

For example, the path for the MCP server config for the Antigravity MCP client is usually `~/.gemini/antigravity/mcp_config.json`

```json
{
  "mcpServers": {
    "prokn-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://localhost:8000/mcp",
        "--sse",
        "--allow-http"
      ]
    }
  }
}
```

## Build Docker Image
Before deploying the MCP Server to the ProKN Server for production use, test the docker image. The Dockerfile is at [./Dockerfile](./Dockerfile). <br>
1. Build the Docker image using `docker build -t prokn-mcp-server -f tools/mcpserver/Dockerfile tools/mcpserver/`
2. Start the container:
```sh
docker run -d \
  --name prokn-mcp-server \
  -p 8000:8000 \
  -e NEO4J_URI="bolt://host.docker.internal:<neo4j_port>" \
  -e NEO4J_USERNAME="<neo4j_username>" \
  -e NEO4J_PASSWORD="<neo4j_password>" \
  prokn-mcp-server
```

3. Run `docker container ls` and wait for the STATUS to become healthy.
4. Add the same config as in Step 4 of Local Development to your MCP Client's MCP server list.
5. Test the MCP server by running any query on the MCP Client. To see the logs: run `docker logs prokn-mcp-server` in a new terminal session and verify that the server is working as expected.

## Deploying to ProKN Server
To be discussed.
This will likely involve the following steps:
1. Pushing the docker image to a registry or building it on a server
2. Start the docker container and make it listen to some port
3. The reverse proxy (Apache) needs to be updated to route /mcp/ to the docker container (specifically the local port that the docker container is listening on)
4. It can be deployed on a server using:
```sh 
docker run -d --name <container-name> -p <port>:8000 --add-host host.docker.internal:host-gateway -e NEO4J_URI="bolt://host.docker.internal:<neo4j-port>" -e NEO4J_USERNAME="<neo4j-username>" -e NEO4J_PASSWORD=“<neo4j-password>” <image-name>
```

## Usage

1. Once the MCP Server is deployed to ProKN Server, a user would need to add the following config to their MCP client:
```json
{
  "mcpServers": {
    "prokn-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://research.bioinformatics.udel.edu/ProKN/mcp",
        "--sse",
        "--allow-http"
      ]
    }
  }
}
```
2. The MCP Client usually needs to be refreshsed (Google Antigravity) or restarted (Claude Desktop) for the new MCP Server handshake to be completed and the MCP server to be recognized.

## Evaluation
To be discussed. https://github.com/lastmile-ai/mcp-eval looks like a good tool to explore. A tentative plan could be:
1. Check if the results "CONTAIN" the expected answer for the foundational queries.
2. Check if proper tools were called for more complex queries, along with the results contanining the expected answer.
3. Check Response times

These tests could help in evaluation for a manuscript, and also to test for regressions before deploying. Note that for manuscript, the results might depend on which LLM the MCP Client uses and multiple runs might be needed to make observations robust. 

## Some Observations

## TODOs / Discussion Items
- [x] Check if we can use a MCP server that is written in Python with our current stack. -> We can if we point our reverse proxy at it. We don't necessarily need to use Node.js for the MCP server and [Python FastMCP](https://github.com/PrefectHQ/fastmcp) seems to have plenty of support and community around it.
- [ ] Do we need authentication and authorization? We can add FastMCP Supported [Rate Limiting](https://gofastmcp.com/python-sdk/fastmcp-server-middleware-rate_limiting) to prevent misuse (DOD Attacks etc.)
- [ ] Check about other security considerations and why Mount Sinai Center for Biomedical Informatics didn't make the MCP Server public rather just the ChatBot Interface.
- [ ] Can we have an interface on the ProKN website to render the results of Cypher queries in case a user wants to validate the results and dig deeper? Right now we support only SPARQL queries.

## High-Level Design Decisions

1. Can we have a Chatbot Interface for ProKN to enable LLM driven knowledge graph queries? 
    - We can have a ChatBot use the same MCP Server. 
    Pros: 
    1. We might have a more curated System Prompt for making the tool calls.
    2. We may be able to render some results (that adhere to a certain structure) in an interactive way (like a table or a graph) on the ProKN website. This is done on the CFDE Workbench: https://data.cfde.cloud/chat. 
    Cons:
    1. We have to bear the cost of tokens. In addition we need to add additional security measures to prevent prompt injection attacks, unintended and generic use of LLMs, etc.
    2. If we don't expose the MCP Server directly to users, they might not be able to connect data across different MCP Servers to enable cross-resource discovery. 

2. Tool Design
    1. We could use the Neo4j MCP Server out of the box. It supports at a high level only two important tools - get schema and run cypher. The schema of our knowledge graph is extremely big and would consume significant time and tokens. In addition, the run_cypher tool is very generic. 
    2. For now, we are thus exploring creating a custom MCP Server with foundational tools to enable the usecases at https://research.bioinformatics.udel.edu/ProKN/usecases. These tools can be also used in combination for other use cases. We still have a generic run cypher tool that can be used in case we need to run arbitrary cypher queries that our tools cannot support. To get the schema, we currently have tools to get a compressed schema. However, this might need additional work based on the performance on arbitrary queries by the LLM.