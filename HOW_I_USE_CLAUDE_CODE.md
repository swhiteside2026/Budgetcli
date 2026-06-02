# How I Use Claude Code
by Samya Whiteside

I started this curriculum not knowing what Claude Code was beyond a fancy AI assistant. What I didn't expect was how technical it actually is — and how much it can genuinely do. It doesn't just answer questions. It reads your files, writes real code, runs tests, pushes to GitHub, and catches bugs you didn't know existed. That was the biggest surprise for me.

Over 27 days I built a complete personal budget tracker called Budgetcli from scratch. It started as a simple command line tool and grew into something with 11 commands, budget limits with warnings, recurring transactions, color-coded terminal output, date filtering, CSV export, and a web dashboard preview. I also built custom slash commands — my favorite being /budget-review, which runs three commands and writes me a plain English paragraph about my financial health in seconds. What used to take 20 minutes now takes one command.

The most important thing I learned is that your prompt is everything. Claude Code is powerful but it only knows what you tell it. If you leave something out, it will fill in the gaps the best it can — and sometimes that's not what you wanted. The fix is simple: cover everything in your initial prompt. Be specific about what you want, what you don't want, and any constraints that matter. When I did that, Claude rarely fell short.

I also learned when NOT to use it. I built the delete transaction command myself without Claude and it took 30 minutes and 3 errors. Claude would have done it in 2 minutes. But I understood every line I wrote — and I didn't understand half of what Claude wrote for the edit command. Speed and understanding are a tradeoff. Know which one you need before you start.

If you've never used Claude Code, try it. It's a genuine time saver and it will change how you think about building things. Just remember — you're still the one in charge. Review every diff, question every suggestion, and don't let it make decisions you don't understand. Claude Code is a tool. A very powerful one. But the thinking still has to be yours.
