# MCP Module – Sessions 30, 31 & 32 – Trainer Guide

This guide describes how to deliver three linked MCP sessions using the completed slide
decks and code in this pack. Trainers do **not** need to create or modify slides – all
essential content is already included in the PPTX files.

## Assets

- slides/MCP_Architecture.pptx
  - Session 30: MCP Architecture & First MCP Server
- slides/MCP_Containerization_Connection.pptx
  - Session 31: MCP Containerization & Connection
- slides/MCP_Case_Study_2_HR_Leave_Assistant.pptx
  - Session 32: Case Study 2 – HR Leave Assistant
- code/main.py
  - Simple in-memory LeaveManager MCP server
- code/main_v2.py
  - SQLite-backed HRLeaveManager MCP server
- code/pyproject.toml, code/README.md, environment files

The **HR Leave Assistant** story is shared across all sessions, so learners see a coherent arc:

1. Session 30 – Understand MCP architecture and run the first MCP server.
2. Session 31 – Containerise and connect a richer MCP server with a database.
3. Session 32 – Extend HRLeaveManager in a case study and present solutions.

Trainers only need to:
- Walk through the slides in order.
- Run the provided code for demos.
- Guide learners through the suggested labs.

---

## Session 30 – MCP Architecture & First MCP Server (3 hours)

**Deck:** slides/MCP_Architecture.pptx  
**Code focus:** code/main.py

### Learning outcomes

By the end of Session 30, learners should be able to:

- Explain what MCP is and where it sits in an agentic AI stack.
- Use core MCP vocabulary: host, client, server, tools, resources, prompts, transport.
- Read an MCP architecture diagram and describe the end-to-end request flow.
- Run a simple MCP server and call its tools from an MCP-enabled client.
- Make a small change to an MCP server (e.g., add a new tool).

These outcomes are already captured on the **“Session 30 – Outcomes”** slide.

### Slide flow

Recommended flow through MCP_Architecture.pptx:

1. **Intro + Outcomes**
   - Use the title and “Session 30 – Outcomes” slides to set context and expectations.
2. **Agents & MCP Concepts**
   - Use the “Recap – Agents & Tools” slide to connect with earlier agent modules.
   - Use the existing architecture slides to explain host, client, server, and transport.
3. **Lifecycle & JSON-RPC**
   - Use “MCP Lifecycle – High-Level” and “JSON-RPC in MCP – Simplified Example”
     to show how a single tool call flows through the system.
4. **Architecture → Code**
   - Use “Architecture → Code: LeaveManager Server” to map concepts to `main.py`.
   - Switch to your IDE to briefly show `FastMCP("LeaveManager")`, tools, resource, prompt.
5. **Running the Server**
   - Use “Running the LeaveManager MCP Server” to walk learners through the commands.
6. **Labs**
   - Use “Lab 1 – Run & Explore LeaveManager” and “Lab 2 – Add a New Tool” slides to
     explain the exercises.
7. **Q&A**
   - Close on “Q&A and Common Pitfalls”.

### Suggested timing

- 0:00–0:20 – Overview of MCP and agent recap.
- 0:20–0:45 – Architecture, lifecycle, and JSON-RPC example.
- 0:45–1:05 – Architecture → code walkthrough (`main.py`) + running the server.
- 1:05–1:15 – Break.
- 1:15–1:45 – Lab 1: run and explore tools.
- 1:45–2:25 – Lab 2: add a new tool.
- 2:25–3:00 – Group discussion, recap, Q&A.

---

## Session 31 – MCP Containerization & Connection (3 hours)

**Deck:** slides/MCP_Containerization_Connection.pptx  
**Code focus:** code/main_v2.py

### Learning outcomes

Learners will:

- Explain why containerisation is useful for MCP servers.
- Describe MCP tools, resources, prompts and lifecycle as system capabilities.
- Build and run a Docker image for an MCP server.
- Connect an MCP host/client to a containerised server.
- Discuss benefits and limitations of MCP in production.

These outcomes appear on the **“Session 31 – Outcomes”** slide.

### Slide flow

1. **Intro + Outcomes**
   - Title and outcomes slides.
2. **Concepts & Use Cases**
   - Use the existing slides on MCP capabilities, benefits, limitations, and use cases.
3. **HRLeaveManager Overview**
   - Use “HRLeaveManager – A Realistic MCP Server” to explain the DB-backed design
     and expanded toolset in `main_v2.py`.
4. **Installing & Connecting MCP Server**
   - Use “Installing an MCP Server with mcp[cli]” to discuss registration/config.
5. **Docker Basics & Example Dockerfile**
   - Use “Dockerizing HRLeaveManager – Example Dockerfile” and
     “Building and Running the Container” to walk through the commands.
6. **Security & Data Protection**
   - Use the dedicated slide to anchor a discussion on access, secrets and logging.
7. **Lab – Containerise & Connect**
   - Use the lab slide to guide the hands-on portion.
8. **Prep for Case Study**
   - Use “Preparing for Case Study 2” to collect ideas for Session 32.

### Suggested timing

- 0:00–0:20 – Recap MCP + introduce HRLeaveManager v2.
- 0:20–0:40 – Walk through tools, DB, and prompts in `main_v2.py`.
- 0:40–1:05 – Docker concepts and example Dockerfile.
- 1:05–1:15 – Break.
- 1:15–1:45 – Build and run container; connect from MCP client.
- 1:45–2:25 – Lab: containerise & connect.
- 2:25–3:00 – Discussion, focus on production concerns, prep for case study.

---

## Session 32 – Case Study 2: HR Leave Assistant End-to-End (3 hours)

**Deck:** slides/MCP_Case_Study_2_HR_Leave_Assistant.pptx  
**Code focus:** extend code/main_v2.py

This session is team-based and highly applied.

### Learning outcomes

Learners will:

- Map a business problem to MCP tools, resources and prompts.
- Extend an MCP server with new, realistic capabilities.
- Run their extended server in a containerised environment.
- Present and defend their design and implementation.

These are reflected on the **Session 32 – Outcomes** slide.

### Slide flow

1. **Title + Outcomes**
   - Introduce the case study and what success looks like.
2. **Case Study Brief**
   - Use the brief slide plus the `docs/Case_Study_2_Brief_for_Students.md` handout.
3. **Existing Capabilities Recap**
   - Remind learners what HRLeaveManager already does.
4. **Improvement Ideas**
   - Walk through possible improvements; teams may choose from these or propose their own.
5. **Team Tasks**
   - Clarify the step-by-step tasks: design, implement, containerise, demo.
6. **Assessment Rubric**
   - Make grading / expectations explicit.
7. **Demo Structure**
   - Give teams a simple pattern for their 5-minute presentations.
8. **Wrap-Up**
   - Connect this case study back to the overall module and real-world use.

### Suggested timing

- 0:00–0:15 – Recap, brief, and Q&A.
- 0:15–0:30 – Teams choose improvements and plan their design.
- 0:30–1:15 – Implementation in `main_v2.py` and local testing.
- 1:15–1:30 – Break.
- 1:30–2:15 – Containerise updated server and finalise demos.
- 2:15–2:45 – Team demos (5–7 minutes each).
- 2:45–3:00 – Feedback, overall recap, next steps.

---

## General delivery tips

- Keep referring back to the HR Leave Assistant story so content stays concrete.
- Use the code only to illustrate key ideas; you don’t need to dive into every line.
- Encourage learners to think about security and data limits whenever they design new tools.
- If time is short, prioritise demos and conceptual understanding over writing lots of code.

With these decks and code, you can run all three sessions without creating additional slides.
