#!bin/bash
SHELL_VER=$(bash --version | head -1)
CTX="SHELL_CONTEXT:
  shell: bash
  version: $SHELL_VER
  os: $(uname -s)
  line_continuation: backslash at end of line
  heredoc: <<'EOF'...EOF
  path_separator: forward slash
  encoding: utf-8

When generating multi-line code, ALWAYS use bash syntax.
Never use PowerShell backtick continuation.
Never use @'...'@ here-strings.
Output code in a single \`\`\`bash fenced block."

ollama run "$1" "$CTX

Ready. Ask me anything."
