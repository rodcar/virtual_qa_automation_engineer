# Virtual QA Automation Engineer

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage (CLI)](#usage)
- [Using the UI](#using-the-ui)
- [Architecture](#architecture)
- [Cypress Testing](#cypress-testing)
  - [Output Folder](#output-folder)
  - [Cypress Configuration](#cypress-configuration)
  - [Running Cypress Tests](#running-cypress-tests)
- [Eval](#eval)
- [License](#license)

This example demonstrates a virtual QA automation engineer that analyzes web pages, generates test plans, and creates test automation code.

## Features

- Systematically explores websites and identifies test cases
- Generates comprehensive test plans for web applications
- Creates Cypress JS test automation code for identified test cases
- Generates visually appealing markdown test plans
- Analyzes web page content, elements, and functionality
- Navigates through website links to map application flow

## Requirements

- Python 3.11+
- AIQ Toolkit installed
- OpenAI API key (set as OPENAI_API_KEY environment variable)

## Installation

1. Clone the [NVIDIA/AIQToolkit](https://github.com/NVIDIA/AIQToolkit) repository.
```bash
git clone https://github.com/NVIDIA/AIQToolkit.git
```

2. Navigate to the `AIQToolkit/examples` folder and clone this repository
```bash
cd AIQToolkit/examples

git clone https://github.com/rodcar/virtual_qa_automation_engineer.git

# Navigate to the project's folder
cd virtual_qa_automation_engineer/
```

3. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use .venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -e .
```

From here you can choose to run the agent using the terminal or the UI.

## Usage (CLI)

**This tutorial assumes that the project folder is inside the "examples" folder from [NVIDIA/AIQToolkit](https://github.com/NVIDIA/AIQToolkit).**

To run the virtual QA automation engineer, include the URL in your request:

```bash
# Set your OpenAI API key first
export OPENAI_API_KEY=your_openai_api_key

# Then run the QA automation engineer
aiq run --config_file=configs/workflow.yaml --input "Generate a test plan for https://rodcar.github.io/girl-factor/"
```

## Using the UI

The AIQ Toolkit provides a user interface that makes it easier to interact with the virtual QA automation engineer.

> **Note:** The UI is located in the `external/aiqtoolkit-opensource-ui` directory. Make sure to run the UI commands from this directory.

In a new terminal:

1. Install the required dependencies:
```bash
# In the AIQ Toolkit root directory
npm install
```

2. Start the UI:
```bash
# In the aiqtoolkit-opensource-ui directory
npm run dev
```

3. In a new terminal: Start the AIQ server:
```bash
# Set your OpenAI API key first
export OPENAI_API_KEY=your_openai_api_key

# In a separate terminal, from the AIQToolkit folder
aiq serve --config_file examples/virtual_qa_automation_engineer/configs/workflow.yaml
```

4. Open the UI in your browser at http://localhost:3000 (or the port shown in your terminal)

5. Configure the connection settings in the UI (If necessary):
   - Set the HTTP API endpoint (typically http://localhost:8000)

6. Enter your test request with a URL to start generating test plans and automation code
"Generate a test plan for https://rodcar.github.io/girl-factor/"

## Architecture

The virtual QA automation engineer uses a React Agent workflow with three main tools:
- `web_navigator`: Fetches and analyzes web page content
- `generate_test_automation_code`: Creates Cypress JS test automation code
- `generate_test_plan_markdown`: Generates visually rich markdown test plans

The agent systematically explores web pages, extracts links, navigates through the website, identifies test cases, and generates test automation code for each identified test case. It then creates a comprehensive test plan in markdown format as its final output.

> **Note:** The current system prompt limits the number of test cases for which Cypress JS test automation code is generated to 10. This means that, regardless of how many test cases are identified during exploration, only the first 10 will have automation code generated in each run. This is by design to ensure efficiency and manageability of the generated output.

## Cypress Testing

### Output Folder

The agent generates Cypress test files in the `output` directory. These files are automatically configured in the Cypress test runner through the project's `cypress.config.js` file, which includes this path in its `specPattern`.

### Cypress Configuration

The project uses a `cypress.config.js` file at the root to configure the test runner:

```javascript
const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    specPattern: [
      "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}",
      "examples/virtual_qa_automation_engineer/output/**/*.cy.js"
    ],
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
```

This configuration includes both standard Cypress test locations and the test files generated by the virtual QA engineer.

### Running Cypress Tests

Once the agent has generated test files, you can run them using the Cypress test runner:

```bash
# Run tests in headless mode
npx cypress run

# Or open the Cypress Test Runner UI
npx cypress open
```

## Eval

To run the evaluation for the virtual QA automation engineer, set your OpenAI API key and execute the following command:

```bash
export OPENAI_API_KEY=your_openai_api_key
aiq eval --config_file examples/virtual_qa_automation_engineer/configs/eval_config.yml
```

The evaluation uses the `eval_dataset.json` file located in `virtual_qa_automation_engineer/data/`. This file contains a set of evaluation prompts (such as test plan requests for specific URLs) and their expected answers. The evaluation process compares the agent's generated outputs against these expected answers to assess performance and accuracy.

## License

This example is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
