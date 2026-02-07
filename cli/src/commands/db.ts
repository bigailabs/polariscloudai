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
import { select, input, confirm } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerDbCommand(program: Command) {
  const db = program
    .command("db")
    .description("Manage databases");

  db.command("list")
    .alias("ls")
    .description("List your databases")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching databases...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const data = await client.getUserStorage();
        spinner.stop();

        if (json) {
          printJson(data);
          return;
        }

        printInfo(
          "Managed databases coming soon. Storage volumes are available now.",
        );
        if (data.volumes && data.volumes.length > 0) {
          printTable(
            ["ID", "Bucket", "Size", "Created"],
            data.volumes.map((v: any) => [
              v.id?.slice(0, 8) || "—",
              v.bucket_name,
              formatBytes(v.size_bytes || 0),
              v.created_at ? new Date(v.created_at).toLocaleDateString() : "—",
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

  db.command("create")
    .description("Create a new database")
    .option("--engine <engine>", "Database engine (pg, redis, mongodb)")
    .option("--name <name>", "Database name")
    .option("--region <region>", "Region", "lagos")
    .action(async (opts) => {
      const json = program.opts().json;

      const engine =
        opts.engine ||
        (await select({
          message: "Database engine:",
          choices: [
            { name: "PostgreSQL", value: "pg" },
            { name: "Redis", value: "redis" },
            { name: "MongoDB", value: "mongodb" },
          ],
        }));

      const name =
        opts.name ||
        (await input({
          message: "Database name:",
          default: `${engine}-${Date.now().toString(36).slice(-4)}`,
        }));

      if (json) {
        printJson({
          message: "Managed databases coming soon",
          engine,
          name,
          region: opts.region,
        });
      } else {
        printInfo("Managed databases are coming soon.");
        printInfo(
          "Track progress at: https://polaris.computer/dashboard",
        );
      }
    });

  db.command("delete <id>")
    .description("Delete a database")
    .option("-y, --yes", "Skip confirmation")
    .action(async (id, opts) => {
      if (!opts.yes) {
        const ok = await confirm({
          message: `Delete database ${id}? This cannot be undone.`,
          default: false,
        });
        if (!ok) {
          printInfo("Cancelled.");
          return;
        }
      }

      printInfo("Managed database deletion coming soon.");
    });

  db.command("connect <id>")
    .description("Get connection string for a database")
    .action(async (id) => {
      printInfo("Managed databases coming soon.");
    });
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
