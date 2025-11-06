# github-cicd-pipeline/README.md

# GitHub CI/CD Pipeline

This project demonstrates a Continuous Integration and Continuous Deployment (CI/CD) pipeline using GitHub Actions. It includes workflows for building, testing, and deploying an application.

## Project Structure

```
github-cicd-pipeline
├── .github
│   └── workflows
│       ├── build.yml
│       ├── deploy.yml
│       └── test.yml
├── scripts
│   ├── build.sh
│   ├── deploy.sh
│   └── test.sh
├── tests
│   └── unit
│       └── test_app.js
├── src
│   └── poll_sync.py
├── package.json
├── .env.example
├── .gitignore
└── README.md
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/github-cicd-pipeline.git
   cd github-cicd-pipeline
   ```

2. **Install dependencies:**
   ```bash
   **Amazon Linux:**
   sudo yum install python3 python3-pip -y
   npm install
   pip3 install pymongo
   pip3 install pymongo python-dotenv tqdm
   pip install boto3
   pip install motor
   pip3 install --upgrade requests urllib3 chardet
   ```

3. **Create a `.env` file:**
   Copy the `.env` to `.env` and fill in the required environment variables.

4. **Run the application:**
   ```bash
   nohup python3.7 poll_sync.py > sync.log 2>&1 &
 
   ```

## CI/CD Workflows

- **Build Workflow:** Defined in `.github/workflows/build.yml`, this workflow compiles the application whenever code is pushed to the repository.

- **Test Workflow:** Defined in `.github/workflows/test.yml`, this workflow runs the test scripts to ensure code quality and functionality.

- **Deploy Workflow:** Defined in `.github/workflows/deploy.yml`, this workflow deploys the application to the specified environment after a successful build.

## Contribution Guidelines

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your branch and create a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
