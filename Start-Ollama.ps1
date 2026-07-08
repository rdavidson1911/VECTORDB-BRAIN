<#
Summary: Adding a prompot injection pattern into pwsh when working with ollama llm models
Author: rpd
Date: 2026-05-30
Version: 0.1.1.
Tested: False



#>


$CTX = @"

SHELL_CONTEXT:
shell: pwsh
version: $($PSVersionTable.PSVersion)
os: windows
line_continuation: backtick (```)
heredoc: @'...'@ or @"..."@
path_separator: backslash
encoding: utf-8

When generating multi-line code, ALWAYS use PowerShell syntax.
Never use bash line contniuation (backslash at the end of line).
Never use bash heredoc (<<EOF).
Output code in a single ```powershell fenced block.
"@

ollama run $args[0] "$CTX'n'nReady. Ask me anything."
