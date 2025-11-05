# AI Assistant Preferences

## Context Usage
Keep preferences brief to preserve context for other tasks.

## Database AI(aka DbAI) to Dashboard AI(aka DashAI) Communication
When asked to create a prompt for another AI, generate a comprehensive, technical prompt that includes:
- **ALWAYS use plaintext format in a code block (text box) in the chat window for easy copying** - DO NOT write prompts to files unless explicitly requested
- Clear subject and context
- Current working status (what's already implemented)
- Specific missing requirements with technical details
- Expected API endpoints with parameters and response formats
- Priority levels (HIGH/MEDIUM/LOW)
- Expected impact and benefits
- Technical requirements (HTTPS, CORS, performance, etc.)
- Contact information and current integration status
- Include specific examples of current vs needed data structures
- Provide clear success criteria and testing requirements

### Prompt Delivery Format
- **Format**: Plain text in a markdown code block (```) in the chat window
- **Purpose**: Easy copying for user to paste into another AI/system
- **Do NOT**: Write prompts to files unless user explicitly asks to save them
- **Do**: Present the complete prompt in a code block that can be copied directly

---

**Version**: v1.19.9  
**Last Updated**: November 4, 2025 21:50 UTC  
**Maintainer**: ES Inventory Hub Team
