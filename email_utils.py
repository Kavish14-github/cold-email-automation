import os
from dotenv import load_dotenv
from fastapi import HTTPException
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_email(company_name: str, job_title: str, job_description: str, resume_text: str) -> str:
    """Generate a personalized cold email using OpenAI."""
    prompt = f"""Based on the following resume and job details, write a personalized cold email that:
1. Shows genuine interest in the company and role
2. Highlights relevant experience from the resume
3. Maintains a professional yet conversational tone
4. Is concise and impactful
5. Ends with a clear call to action

Resume:
{resume_text}

Job Details:
Company: {company_name}
Position: {job_title}
Description: {job_description}

Write the email body only, without subject line or signature."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional email writer specializing in cold outreach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")

def generate_followup(company_name: str, job_title: str, original_email: str, resume_text: str) -> str:
    """Generate a follow-up email using OpenAI."""
    prompt = f"""Based on the following information, write a professional follow-up email that:
1. References the original email
2. Maintains interest in the position
3. Adds new value or information
4. Is concise and respectful
5. Has a clear call to action

Company: {company_name}
Position: {job_title}
Original Email:
{original_email}

Resume:
{resume_text}

Write the email body only, without subject line or signature."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional email writer specializing in follow-up communications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up: {str(e)}")

def send_email(recipient: str, subject: str, body: str):
    """Send email using configured email service."""
    # Implement your email sending logic here
    # For now, we'll just print the email details
    print(f"Sending email to {recipient}")
    print(f"Subject: {subject}")
    print(f"Body: {body}") 