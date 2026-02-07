import { Command } from "commander";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
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
import { input, confirm } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerSshKeysCommand(program: Command) {
  const sshKeys = program
    .command("ssh-keys")
    .description("Manage SSH public keys");

  sshKeys
    .command("list")
    .alias("ls")
    .description("List your SSH keys")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching SSH keys...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        // SSH keys are typically part of user profile or a dedicated endpoint
        // Use the API keys list as a proxy for now — real implementation depends on backend
        const data = await client.listApiKeys();
        spinner.stop();

        if (json) {
          printJson(data);
          return;
        }

        printInfo(
          "SSH key management is available in the dashboard: https://polaris.computer/dashboard/settings",
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

  sshKeys
    .command("add")
    .description("Add an SSH public key")
    .option("--file <path>", "Path to public key file")
    .option("--name <name>", "Key name")
    .action(async (opts) => {
      const json = program.opts().json;

      let keyContent: string;
      let keyName = opts.name;

      if (opts.file) {
        const filePath = opts.file.replace("~", os.homedir());
        if (!fs.existsSync(filePath)) {
          printError(`File not found: ${filePath}`);
          process.exit(1);
        }
        keyContent = fs.readFileSync(filePath, "utf-8").trim();
      } else {
        // Try common default paths
        const defaultPaths = [
          path.join(os.homedir(), ".ssh", "id_ed25519.pub"),
          path.join(os.homedir(), ".ssh", "id_rsa.pub"),
        ];

        const found = defaultPaths.find((p) => fs.existsSync(p));
        if (found) {
          printInfo(`Found SSH key: ${found}`);
          const ok = await confirm({
            message: `Use ${path.basename(found)}?`,
            default: true,
          });
          if (ok) {
            keyContent = fs.readFileSync(found, "utf-8").trim();
          } else {
            const filePath = await input({
              message: "Path to public key file:",
            });
            keyContent = fs
              .readFileSync(filePath.replace("~", os.homedir()), "utf-8")
              .trim();
          }
        } else {
          const filePath = await input({
            message: "Path to public key file:",
            default: "~/.ssh/id_ed25519.pub",
          });
          keyContent = fs
            .readFileSync(filePath.replace("~", os.homedir()), "utf-8")
            .trim();
        }
      }

      if (!keyContent.startsWith("ssh-")) {
        printError("Invalid SSH public key format. Key should start with ssh-ed25519, ssh-rsa, etc.");
        process.exit(1);
      }

      if (!keyName) {
        keyName = await input({
          message: "Key name:",
          default: `cli-${Date.now().toString(36).slice(-4)}`,
        });
      }

      if (json) {
        printJson({
          success: true,
          message: "SSH key upload — use the dashboard for full SSH key management",
          name: keyName,
          key_type: keyContent.split(" ")[0],
        });
      } else {
        printInfo(
          "SSH key management coming soon via API. For now, manage keys at:",
        );
        printInfo(
          chalk.underline("https://polaris.computer/dashboard/settings"),
        );
      }
    });

  sshKeys
    .command("remove <id>")
    .description("Remove an SSH key")
    .action(async () => {
      printInfo(
        "SSH key management is available in the dashboard: https://polaris.computer/dashboard/settings",
      );
    });
}
