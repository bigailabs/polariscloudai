import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import {
  printTable,
  printJson,
  printSuccess,
  printError,
  printInfo,
} from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { input, confirm, select } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerStorageCommand(program: Command) {
  const storage = program
    .command("storage")
    .description("Manage storage buckets");

  storage
    .command("list")
    .alias("ls")
    .description("List your storage volumes")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching storage...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const data = await client.getUserStorage();
        spinner.stop();

        if (json) {
          printJson(data);
          return;
        }

        if (!data.volumes || data.volumes.length === 0) {
          printInfo("No storage volumes found.");
          printInfo("Create one with: polaris storage create");
          return;
        }

        printTable(
          ["Bucket", "Provider", "Size", "Created"],
          data.volumes.map((v: any) => [
            v.bucket_name,
            v.provider || "storj",
            formatBytes(v.size_bytes || 0),
            v.created_at ? new Date(v.created_at).toLocaleDateString() : "—",
          ]),
        );
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

  storage
    .command("create")
    .description("Create a new storage bucket")
    .option("--name <name>", "Bucket name")
    .option("--region <region>", "Region", "lagos")
    .option("--access <access>", "Access level (private, public-read)")
    .action(async (opts) => {
      const json = program.opts().json;

      const name =
        opts.name ||
        (await input({
          message: "Bucket name:",
          validate: (v) =>
            /^[a-z0-9][a-z0-9.-]+$/.test(v) || "Lowercase letters, numbers, dots, hyphens",
        }));

      const access =
        opts.access ||
        (await select({
          message: "Access level:",
          choices: [
            { name: "Private (default)", value: "private" },
            { name: "Public read", value: "public-read" },
          ],
        }));

      if (json) {
        printJson({ message: "Storage creation via CLI coming soon", name, access });
      } else {
        printInfo("Storage bucket creation via CLI is coming soon.");
        printInfo(
          "Manage storage at: https://polaris.computer/dashboard",
        );
      }
    });

  storage
    .command("delete <name>")
    .description("Delete a storage bucket")
    .option("-y, --yes", "Skip confirmation")
    .action(async (name, opts) => {
      if (!opts.yes) {
        const ok = await confirm({
          message: `Delete bucket "${name}"? This cannot be undone.`,
          default: false,
        });
        if (!ok) {
          printInfo("Cancelled.");
          return;
        }
      }

      printInfo("Storage deletion via CLI is coming soon.");
    });
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}
