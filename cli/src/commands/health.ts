import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import { printSuccess, printError, printKeyValue, printJson } from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerHealthCommand(program: Command) {
  program
    .command("health")
    .description("Check Polaris Cloud API status")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Checking API status...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const health = await client.health();
        spinner.stop();

        if (json) {
          printJson(health);
        } else {
          const statusIcon =
            health.status === "healthy"
              ? chalk.green("●")
              : chalk.red("●");

          console.log(`${statusIcon} ${health.service} v${health.version}`);
          console.log();
          printKeyValue({
            Status: health.status,
            Database: health.database,
            "Demo Mode": health.demo_mode ? "yes" : "no",
            Auth: health.auth_enabled ? "enabled" : "disabled",
          });
        }
      } catch (err) {
        spinner.stop();
        if (json) {
          printJson({
            status: "unreachable",
            error: err instanceof PolarisApiError ? err.detail : String(err),
          });
        } else {
          printError(
            err instanceof PolarisApiError
              ? err.toUserMessage()
              : `Could not reach API: ${err}`,
          );
        }
        process.exit(1);
      }
    });
}
