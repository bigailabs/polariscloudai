import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import {
  printTable,
  printJson,
  printKeyValue,
  printSuccess,
  printError,
  printInfo,
} from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerBillingCommand(program: Command) {
  const billing = program
    .command("billing")
    .description("Billing and subscription info");

  billing
    .command("plans")
    .description("List subscription plans")
    .action(async () => {
      const json = program.opts().json;

      const plans = [
        {
          name: "Free",
          price: "$0/mo",
          compute: "30 min",
          storage: "—",
          api_keys: "3",
        },
        {
          name: "Basic",
          price: "$10/mo",
          compute: "300 min",
          storage: "10 GB",
          api_keys: "10",
        },
        {
          name: "Premium",
          price: "$20/mo",
          compute: "1000 min",
          storage: "100 GB",
          api_keys: "25",
        },
      ];

      if (json) {
        printJson(plans);
        return;
      }

      printTable(
        ["Plan", "Price", "Compute", "Storage", "API Keys"],
        plans.map((p) => [p.name, p.price, p.compute, p.storage, p.api_keys]),
      );

      console.log(
        chalk.dim("\n  Upgrade at: https://polaris.computer/pricing\n"),
      );
    });

  billing
    .command("status")
    .description("Show your current subscription")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching billing info...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const stats = await client.getStats();
        spinner.stop();

        if (json) {
          printJson(stats);
          return;
        }

        console.log();
        printKeyValue({
          Plan: stats.tier.charAt(0).toUpperCase() + stats.tier.slice(1),
          "Compute Used": `${stats.compute_minutes_used} / ${stats.compute_minutes_limit} min`,
          "Storage Used": `${formatBytes(stats.storage_bytes_used)} / ${formatBytes(stats.storage_bytes_limit)}`,
          "Active Deployments": String(stats.active_deployments),
          "API Keys": String(stats.api_keys_count),
        });
        console.log();
      } catch (err) {
        spinner.stop();
        printError(
          err instanceof PolarisApiError
            ? err.toUserMessage()
            : String(err),
        );
        process.exit(1);
      }
    });

  billing
    .command("transactions")
    .description("View payment history")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching transactions...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const usage = await client.getUsage();
        spinner.stop();

        if (json) {
          printJson(usage);
          return;
        }

        console.log();
        printKeyValue({
          "Total Requests": String(usage.total_requests),
          "This Month": String(usage.this_month),
          "Last Month": String(usage.last_month),
        });

        if (usage.key_usage && usage.key_usage.length > 0) {
          console.log(chalk.dim("\n  Usage by API key:\n"));
          printTable(
            ["Key", "Requests", "Last Used"],
            usage.key_usage.map((k) => [
              k.name,
              String(k.total_requests),
              k.last_used
                ? new Date(k.last_used).toLocaleDateString()
                : "Never",
            ]),
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
    });
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
