# AWS Basics – Infrastructure Automation Project

This project demonstrates the foundational use of AWS IaaS services via automation using the **Boto3 SDK in Python**. It showcases how to programmatically manage cloud infrastructure, including the provisioning and cleanup of resources.

## 🚀 Features

- Automatically creates:
  - 🖥️ **EC2 Instance** (Ubuntu t2.micro)
  - 📦 **S3 Bucket**
  - 📬 **SQS FIFO Queue**
- Uploads a test file (`CSE546test.txt`) to S3
- Sends and receives messages from the SQS queue
- Lists and verifies all active AWS resources
- Cleans up all created resources at the end
- Includes real-time status updates via printed messages

## 🧰 Tech Stack

- **Language**: Python
- **AWS SDK**: [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- **Cloud Provider**: Amazon Web Services (AWS)

## 🛠 Setup Instructions

1. Install dependencies:
   ```bash
   pip install boto3
   ```

2. [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

3. Configure your credentials:
   ```bash
   aws configure
   ```

4. Ensure you have permission to create and delete EC2, S3, and SQS resources.

5. Check that the AMI ID used in the code is valid for your region.

6. Run the script:
   ```bash
   python main3.py
   ```

## ✅ Notes

- Be sure to allow at least 1–2 minutes for AWS resources to initialize.
- All actions print confirmation messages for traceability.
- Code is modular and easy to extend for additional AWS services.
