import { Command } from "commander";
import { password } from "@inquirer/prompts";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import { getApiKey, saveApiKey, removeCredentials } from "../lib/config-manager.js";
import { printSuccess, printError, printKeyValue, printJson } from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerAuthCommand(program: Command) {
  const auth = program.command("auth").description("Manage authentication");

  auth
    .command("login")
    .description("Authenticate with your API key")
    .option("--key <key>", "API key (or enter interactively)")
    .action(async (opts) => {
      const json = program.opts().json;

      let apiKey = opts.key;
      if (!apiKey) {
        console.log(
          chalk.dim("Get your API key from the dashboard: ") +
            chalk.underline("https://polaris.computer/dashboard/api-keys"),
        );
        console.log();
        apiKey = await password({
          message: "Enter your API key:",
          mask: "*",
        });
      }

      if (!apiKey || !apiKey.trim()) {
        printError("No API key provided.");
        process.exit(1);
      }

      apiKey = apiKey.trim();

      const spinner = createSpinner("Validating API key...");
      spinner.start();

      try {
        const client = new PolarisClient(undefined, apiKey);
        const user = await client.me();
        spinner.stop();

        saveApiKey(apiKey);

        if (json) {
          printJson({ success: true, user });
        } else {
          printSuccess("Authenticated successfully!");
          console.log();
          printKeyValue({
            Email: user.email,
            Name: user.name || "—",
            Tier: user.tier,
          });
        }
      } catch (err) {
        spinner.stop();
        if (err instanceof PolarisApiError && err.statusCode === 401) {
          printError("Invalid API key. Please check and try again.");
        } else if (err instanceof PolarisApiError && err.statusCode === 0) {
          // Connection failed — key might still be valid, save it
          saveApiKey(apiKey);
          printSuccess("API key saved (could not verify — API unreachable).");
        } else {
          printError(
            err instanceof PolarisApiError
              ? err.toUserMessage()
              : String(err),
          );
        }
        process.exit(1);
      }
    });

  auth
    .command("logout")
    .description("Remove stored credentials")
    .action(async () => {
      const json = program.opts().json;
      removeCredentials();
      if (json) {
        printJson({ success: true });
      } else {
        printSuccess("Logged out. Credentials removed.");
      }
    });

  auth
    .command("status")
    .description("Show current authentication status")
    .action(async () => {
      const json = program.opts().json;
      const apiKey = getApiKey();

      if (!apiKey) {
        if (json) {
          printJson({ authenticated: false });
        } else {
          printError("Not authenticated. Run `polaris auth login` to sign in.");
        }
        return;
      }

      const spinner = createSpinner("Checking authentication...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const user = await client.me();
        spinner.stop();

        if (json) {
          printJson({ authenticated: true, user });
        } else {
          printSuccess("Authenticated");
          console.log();
          printKeyValue({
            Email: user.email,
            Name: user.name || "—",
            Tier: user.tier,
            "API Key": apiKey.slice(0, 12) + "..." + apiKey.slice(-4),
          });
        }
      } catch (err) {
        spinner.stop();
        if (json) {
          printJson({ authenticated: false, error: String(err) });
        } else {
          printError(
            err instanceof PolarisApiError
              ? err.toUserMessage()
              : `Auth check failed: ${err}`,
          );
        }
      }
    });
}

// Inline class reference for login (avoids circular import)
import { PolarisClient } from "../lib/api-client.js";
