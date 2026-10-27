# upgaming Talent Growth Program
## Applied AI - AI Investigation Engine Task

### 1. Project Description
Your goal is to create an Artificial Intelligence-based system capable of searching, analyzing, linking information across large volumes of documents, and generating well-reasoned answers.

The project should not be just a simple document chat application (Chat with PDF).

The system must be able to process complex questions that require simultaneously examining multiple sources, comparing different pieces of information, and drawing logical conclusions to provide an answer.

**Example:**
An organization has technical documentation, incident reports, system change history, and other materials.

The user asks a question:
*"Which system changes caused the payment processing delay in March, which services were affected, and which documents confirm this?"*

The system should retrieve the relevant information, link facts present in different documents, and provide an answer with citations to the sources.
If the information is insufficient or contradictory, the system must state this and must not fabricate (hallucinate) facts.

---

### 2. Core Requirements

#### Document Processing
The system must be able to ingest, process, and index various document formats.
**Mandatory:**
*   Support for at least three different file formats.
*   Extraction of text and important metadata from documents.
*   Text segmentation (Chunking).
*   Handling of duplicated information.
*   Adding new documents, updating, and deleting existing documents.
*   Comparison of at least two Chunking strategies.

*You must choose the processing architecture yourself and justify the decisions made.*

#### Vector Database and Search
The project requires the use of a Vector Database or a database with vector search support.
**Possible technologies to use:**
*   Qdrant
*   Pinecone
*   Neon PostgreSQL + pgvector
*   Supabase + pgvector
*   Weaviate
*   Chroma
*   Any other suitable alternative

*Merely using regular SQL text search does not fulfill this requirement.* 
The system must use Embeddings and Semantic Search. Additionally, implementing **Hybrid Search** (combining semantic and keyword-based search) is mandatory.

You must implement at least one custom search or result-ranking algorithmic component. Basing the entire search logic solely on out-of-the-box libraries is not allowed.

#### LLM Integration and RAG
The system must use at least one Large Language Model (LLM).
**Mandatory:**
*   Utilization of a Retrieval-Augmented Generation (RAG) architecture.
*   Combining information retrieved from different documents.
*   Processing complex queries in multiple steps.
*   Generating answers based on appropriate evidence.
*   Implementing a source and citation mechanism.
*   Attempting to detect contradictory information.
*   Refraining from answering in case of insufficient information.
*   Handling communication errors and limitations with the LLM.

The system must include at least one Tool Calling or equivalent structured tool invocation mechanism.
*You are free to choose the model, Prompt Engineering approach, and Frameworks used.*

#### Results Evaluation
The candidate must create their own automated evaluation system.
**Minimum requirements:**
*   At least 40 test questions.
*   Simple and multi-step questions.
*   Questions requiring the linking of multiple documents.
*   Questions for which no answer exists in the data.
*   Questions based on contradictory information.
*   Quantitative evaluation of Retrieval and answer quality.
*   Comparison of at least two different configurations.

Appropriate metrics must be used during evaluation, for example: `Recall@K`, `MRR`, `Answer Correctness`, and `Citation Accuracy`.
You must present not only the results but also their analysis: where the system fails, why, and how it can be improved.

#### Backend and User Interface
The project must have a Python-based Backend and a functional User Interface (UI).
The user must be able to add and manage documents, ask questions, and view the sources of generated answers.
You define the API structure, technological architecture, and UI implementation method yourself.
*Priority is given to functional correctness, code quality, and system reliability over the complexity of visual design.*

---

### 3. Dataset
To complete the project, you should use the dataset attached to this task. The use of additional public data or synthetic documents is also permitted.
**Mandatory:**
*   Processing a minimum of 50,000 documents or independent text records.
*   Retrieving linked information across multiple documents.
*   Retaining and identifying sources.
*   Processing incomplete and contradictory information.
*   Capability for repeatable evaluation.

It is not necessary to use the entire Dataset if it is too large. You can select a reproducible subset and justify your choice.
You can choose one or more of the following datasets if acceptable to you:
*   [HotpotQA](https://huggingface.co/datasets/hotpotqa/hotpot_qa)
*   [Ragbench](https://huggingface.co/datasets/galileo-ai/ragbench)
*   [2WikiMultihopQA](https://huggingface.co/datasets/xanhho/2WikiMultihopQA)
*   [Post-mortems (danluu)](https://github.com/danluu/post-mortems)

---

### 4. Free Hosting and Deployment
The project must be hosted online and accessible via a public link.
You must use a free hosting service or a free tier of a service.
**Possible platforms:**
*   Render
*   Vercel
*   Hugging Face Spaces
*   Koyeb
*   Oracle Cloud Always Free
*   Any other free alternative

The Vector Database can also be hosted on an appropriate platform's free Cloud tier.
**Mandatory:**
*   Actual deployment of the system with a public URL.
*   Proper integration of hosting and the database.
*   Data persistence after application restarts.
*   Protection of API keys and other secrets.
*   Description of the Deployment architecture.
*   Consideration of costs, resources, and free tier limitations.

The project must be capable of being completed without purchasing paid infrastructure. Free hosting limitations (e.g., application sleeping or request limits) are acceptable if they are properly documented and do not prevent the demonstration of core functionality.

---

### 5. Technical Quality
We expect from you:
*   Clear and modular Python code.
*   Proper separation of responsibilities/concerns.
*   Error handling.
*   Automated tests.
*   Proper integration with the database and external APIs.
*   Secure management of environment configuration.
*   Technical documentation.
*   Understanding of system performance and LLM costs.

*The use of specific libraries or design patterns is not mandatory.*

---

### 6. Additional Challenges (Bonus)
The following will be evaluated for bonus points:
*   Comparison of multiple LLMs or Embedding models.
*   Multi-agent or Agentic RAG architecture.
*   More advanced Re-ranking mechanisms.
*   Testing against Prompt Injection.
*   Caching and performance optimization.
*   Streaming responses.
*   Monitoring & Observability.
*   Performance testing on large volumes of data.

*Additional functionality does not replace the core requirements.*

---

### 7. What to Present
Upon completing the task, you must submit:
1.  **GitHub Repository** — Full code and project history.
2.  **Live Demo** — Link to the running application.
3.  **README** — Project description, architecture, running instructions, and justification of technical choices.
4.  **Evaluation Report** — Testing methodology, metrics, results, and analysis.
5.  **AI Usage Report** — Which AI tools were used, how they helped, and what you changed independently.

---

### 8. Interview and Code Defense
The use of AI tools during the execution of the project is permitted.
However, you are fully responsible for the submitted code, regardless of whether you wrote it yourself or an AI tool assisted you.

**During the technical interview, you will be required to:**
*   Explain your architecture.
*   Discuss specific parts of the code in detail.
*   Describe the RAG Pipeline's operation step-by-step.
*   Find and fix errors in the code.
*   Add new functionality or modify existing ones on the spot.
*   Justify algorithms and technical decisions.

*The use of AI assistants is strictly prohibited during the practical part of the interview.*
We will evaluate not only the final product but also the candidate's real technical knowledge and ability to solve problems independently.