# MedQGraph
# Temporal Medical Record Knowledge Graphs for AI-Driven Healthcare Insights

## Project Overview

Medical records and doctor-patient transcripts contain valuable insights that can significantly improve healthcare decision-making. However, these records are often unstructured, making it difficult to extract and analyze patient history over time. Our project proposes a **Temporal Medical Record Knowledge Graph (TMKG)** that transforms doctor transcripts into structured, queryable knowledge graphs. This system enables healthcare professionals to ask complex medical questions spanning multiple patient histories and time periods, unlocking deeper insights for diagnosis, treatment, and research.

## Problem Statement
Currently, medical records exist as disparate text-based documents, making it challenging to:
- Reduce the time required for hospital staff to access and interpret patient medical histories, enabling faster and more accurate treatment decisions.
- Extract meaningful relationships between patient encounters, conditions, and treatments.
- Analyze patient health trajectories over time.
- Perform efficient retrieval of relevant information for clinical decision-making.

Our solution addresses these challenges by leveraging knowledge graph techniques combined with Large Language Models (LLMs) and temporal data representations to structure and organize medical transcripts.

---

## Proposed Solution

Our solution transforms unstructured medical transcripts into a **Temporal Medical Knowledge Graph (TMKG)**. Using the MIMIC dataset, we preprocess data into structured JSON format, construct a knowledge graph with nodes and relationships, and incorporate temporal data for longitudinal tracking. The system enables efficient querying and retrieval of medical insights using vector embeddings and temporal analytics, empowering healthcare professionals with actionable, time-sensitive data.

## Implementation Tools & Frameworks

- **Data Preprocessing**: Python (Pandas)
- **Knowledge Graph Construction**: Neo4j, GraphDB
- **Vector Search**: LangChain
- **Language Model for Text Processing**: OpenAI GPT-4o
- **Frontend**: Electron.js
- **Visualization**: NetworkX, Plotly

---

## Outcomes
- Faster and more accurate treatment decisions for healthcare professionals.
- A functional prototype that converts medical transcripts into a structured temporal knowledge graph.
- A queryable interface where users can ask complex medical questions.
- Demonstration of real-world healthcare insights derived from the graph.

---

## Steps to Set Up the Project

### Prerequisites
1. **Node.js** and **npm** installed on your machine.
2. **Python 3.8+** installed.
3. **Neo4j NoSQL** database set up and running.

### Installation

#### Frontend (Electron.js)
1. Clone the repository:
```
git clone https://github.com/lavanyavijayk/MedQGraph.git
```
2. Navigate to the project directory and install npm packages:
```
npm install
```
3. Insall python packages for AI and knowledge graph generation:
```
pip install -r requirements.txt
```
4. Run the application
```
npm start
```


## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **MIMIC Dataset** for providing realistic medical records.
- **OpenAI GPT-4o** for text processing and transformation.
- **Neo4j** for knowledge graph construction and management.
