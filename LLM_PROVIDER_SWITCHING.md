# LLM Provider Switching Guide

This application now supports both Anthropic Claude and Google Gemini as LLM providers. You can easily switch between them by updating the `.env` file.

## Configuration

The `.env` file controls which LLM provider to use:

```env
# LLM Provider Configuration
# Set to "anthropic" or "gemini"
LLM_PROVIDER=gemini

# Anthropic API Configuration
ANTHROPIC_API_KEY=your_anthropic_key_here

# Google Gemini API Configuration  
GEMINI_API_KEY=your_gemini_key_here
```

## Switching Providers

### To use Google Gemini:
1. Set `LLM_PROVIDER=gemini` in `.env`
2. Add your Google AI Studio API key to `GEMINI_API_KEY`
3. Restart the server

### To use Anthropic Claude:
1. Set `LLM_PROVIDER=anthropic` in `.env`
2. Add your Anthropic API key to `ANTHROPIC_API_KEY`
3. Restart the server

## Getting API Keys

### Google Gemini API Key:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

### Anthropic API Key:
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create a new API key
3. Copy the key to your `.env` file

## Features

Both providers support:
- Conversation history
- Tool-based search functionality
- Course material queries
- Same API endpoints and responses

The application will automatically use the configured provider without any code changes needed.