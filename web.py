services:
  - type: web
    name: file-to-link-bot
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn web:app"
