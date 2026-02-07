import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import { consumeSSEStream } from "../lib/streaming.js";
import {
  printTable,
  printJson,
  printError,
  printInfo,
} from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { input } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";
import * as readline from "node:readline";

const AVAILABLE_MODELS = [
  { id: "llama3.2", name: "Llama 3.2 (3B)", provider: "ollama", context: "128K" },
  { id: "llama3.1", name: "Llama 3.1 (8B)", provider: "ollama", context: "128K" },
  { id: "llama3.1:70b", name: "Llama 3.1 (70B)", provider: "ollama", context: "128K" },
  { id: "mistral", name: "Mistral (7B)", provider: "ollama", context: "32K" },
  { id: "mixtral", name: "Mixtral 8x7B", provider: "ollama", context: "32K" },
  { id: "codellama", name: "Code Llama", provider: "ollama", context: "16K" },
  { id: "deepseek-coder", name: "DeepSeek Coder", provider: "ollama", context: "16K" },
  { id: "phi3", name: "Phi-3", provider: "ollama", context: "128K" },
  { id: "gemma2", name: "Gemma 2", provider: "ollama", context: "8K" },
  { id: "qwen2.5", name: "Qwen 2.5", provider: "ollama", context: "128K" },
];

export function registerAiCommand(program: Command) {
  const ai = program.command("ai").description("AI model inference");

  ai.command("models")
    .description("List available AI models")
    .action(async () => {
      const json = program.opts().json;

      if (json) {
        printJson(AVAILABLE_MODELS);
        return;
      }

      printTable(
        ["Model ID", "Name", "Provider", "Context"],
        AVAILABLE_MODELS.map((m) => [m.id, m.name, m.provider, m.context]),
      );
    });

  ai.command("chat [prompt]")
    .description("Chat with an AI model (streaming)")
    .option("--model <model>", "Model to use", "llama3.2")
    .option("--system <prompt>", "System prompt")
    .action(async (promptArg, opts) => {
      const json = program.opts().json;

      if (promptArg) {
        // One-shot mode
        await runOneShot(program, promptArg, opts, json);
      } else {
        // Interactive mode
        await runInteractive(program, opts, json);
      }
    });
}

async function runOneShot(
  program: Command,
  prompt: string,
  opts: { model: string; system?: string },
  json: boolean,
) {
  const spinner = createSpinner("Thinking...");
  spinner.start();

  try {
    const client = createClient(program.opts().apiUrl);
    const messages: any[] = [];

    if (opts.system) {
      messages.push({ role: "system", content: opts.system });
    }
    messages.push({ role: "user", content: prompt });

    const res = await client.rawFetch("POST", "/api/ai/chat", {
      model: opts.model,
      messages,
      stream: !json,
    });

    spinner.stop();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      printError(
        (err as any).detail || `API error: ${res.status}`,
      );
      process.exit(1);
    }

    if (json) {
      const data = await res.json();
      printJson(data);
      return;
    }

    // Stream tokens to stdout
    if (res.body) {
      console.log();
      await consumeSSEStream(
        res.body,
        (token) => process.stdout.write(token),
        () => console.log("\n"),
      );
    }
  } catch (err) {
    spinner.stop();
    printError(
      err instanceof PolarisApiError
        ? err.toUserMessage()
        : String(err),
    );
    process.exit(1);
  }
}

async function runInteractive(
  program: Command,
  opts: { model: string; system?: string },
  json: boolean,
) {
  console.log(
    chalk.hex("#2D5A47").bold(`\n  Polaris AI Chat`) +
      chalk.dim(` (${opts.model})`),
  );
  console.log(chalk.dim("  Type /quit to exit\n"));

  const messages: any[] = [];

  if (opts.system) {
    messages.push({ role: "system", content: opts.system });
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const askQuestion = (): Promise<string> =>
    new Promise((resolve) => {
      rl.question(chalk.hex("#4A7C59")("you > "), (answer) => {
        resolve(answer);
      });
    });

  while (true) {
    const userInput = await askQuestion();

    if (!userInput.trim()) continue;
    if (userInput.trim() === "/quit" || userInput.trim() === "/exit") {
      console.log(chalk.dim("\nGoodbye!"));
      rl.close();
      break;
    }

    messages.push({ role: "user", content: userInput });

    try {
      const client = createClient(program.opts().apiUrl);
      const res = await client.rawFetch("POST", "/api/ai/chat", {
        model: opts.model,
        messages,
        stream: true,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        printError(
          (err as any).detail || `API error: ${res.status}`,
        );
        continue;
      }

      process.stdout.write(chalk.hex("#2D5A47")("ai > "));

      let fullResponse = "";
      if (res.body) {
        fullResponse = await consumeSSEStream(
          res.body,
          (token) => process.stdout.write(token),
          () => console.log("\n"),
        );
      }

      messages.push({ role: "assistant", content: fullResponse });
    } catch (err) {
      printError(
        err instanceof PolarisApiError
          ? err.toUserMessage()
          : String(err),
      );
    }
  }
}
