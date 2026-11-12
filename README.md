# Credit Risk Analysis

## Project Overview
This project analyzes loan application data to understand approval and refusal patterns and identify high-risk segments.

The dataset contains 49,896 loan applications from the `credit_risk` database. The analysis covers application status, rejection reasons, loan amounts, contract types, and customer segments.

A Streamlit dashboard was built to visualize the key findings and to allow interactive exploration of the data using 20 predefined SQL queries.

## Key Findings
- Total Applications: 49,896
- Approved: 31,885 (63.9%)
- Refused: 8,650 (17.3%)
- Canceled: 8,503 (17.0%)
- Top rejection reason is HC, accounting for about 59% of all refusals.
- Approval rate is around 85% for lower loan amounts and drops to 65.9% for very high amounts.
- Consumer loans have the highest approval rate at 85.7%, followed by Revolving loans at 50.6% and Cash loans at 42.8%.

## Tools Used
- Python
- Pandas
- SQL (MySQL)
- Streamlit
- Jupyter Notebook

## Project Structure
- data_cleaning.ipynb - Data Cleaning and Exploratory Data Analysis
- app.py - Streamlit Dashboard Application
- queries.sql - List of 20 SQL Queries used in the project
- requirements.txt - List of required Python libraries

## How to Run This Project
```bash
pip install -r requirements.txt
streamlit run app.py