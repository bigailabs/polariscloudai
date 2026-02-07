import { Command } from "commander";
import { spawn } from "node:child_process";
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
import { confirm } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";

const STATUS_COLORS: Record<string, (s: string) => string> = {
  running: chalk.green,
  pending: chalk.yellow,
  warming: chalk.yellow,
  provisioning: chalk.yellow,
  installing: chalk.cyan,
  stopping: chalk.gray,
  stopped: chalk.gray,
  failed: chalk.red,
};

function colorStatus(status: string): string {
  const colorFn = STATUS_COLORS[status] || chalk.white;
  return colorFn(status);
}

export function registerInstancesCommand(program: Command) {
  const instances = program
    .command("instances")
    .description("Manage your running deployments");

  instances
    .command("list")
    .alias("ls")
    .description("List your deployments")
    .option("--status <status>", "Filter by status")
    .action(async (opts) => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching deployments...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const data = await client.listDeployments();
        spinner.stop();

        let deployments = data.deployments || [];

        if (opts.status) {
          deployments = deployments.filter(
            (d) => d.status === opts.status,
          );
        }

        if (json) {
          printJson(deployments);
          return;
        }

        if (deployments.length === 0) {
          printInfo("No deployments found.");
          printInfo("Deploy one with: polaris deploy");
          return;
        }

        printTable(
          ["ID", "Name", "Template", "Status", "Created"],
          deployments.map((d) => [
            d.id.slice(0, 8),
            d.name,
            d.template_id,
            colorStatus(d.status),
            new Date(d.created_at).toLocaleDateString(),
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

  instances
    .command("get <id>")
    .description("Show deployment details")
    .action(async (id) => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching deployment...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const d = await client.getDeployment(id);
        spinner.stop();

        if (json) {
          printJson(d);
          return;
        }

        console.log(`\n${chalk.bold(d.name)}\n`);
        printKeyValue({
          ID: d.id,
          Template: d.template_id,
          Status: colorStatus(d.status),
          Provider: d.provider,
          Host: d.host || "—",
          Port: d.port ? String(d.port) : "—",
          "Access URL": d.access_url || "—",
          Created: new Date(d.created_at).toLocaleString(),
          Started: d.started_at
            ? new Date(d.started_at).toLocaleString()
            : "—",
        });

        if (d.error_message) {
          console.log(
            `\n${chalk.red("Error:")} ${d.error_message}`,
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

  instances
    .command("terminate <id>")
    .alias("rm")
    .description("Terminate a deployment")
    .option("-y, --yes", "Skip confirmation")
    .action(async (id, opts) => {
      const json = program.opts().json;

      if (!opts.yes) {
        const ok = await confirm({
          message: `Terminate deployment ${id}?`,
          default: false,
        });
        if (!ok) {
          printInfo("Cancelled.");
          return;
        }
      }

      const spinner = createSpinner("Terminating...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const result = await client.deleteDeployment(id);
        spinner.stop();

        if (json) {
          printJson(result);
        } else {
          printSuccess(`Deployment ${id} terminated.`);
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

  // SSH command (top-level alias)
  program
    .command("ssh <id>")
    .description("SSH into a running deployment")
    .action(async (id) => {
      const spinner = createSpinner("Fetching connection info...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const d = await client.getDeployment(id);
        spinner.stop();

        if (d.status !== "running") {
          printError(
            `Deployment is ${d.status}. SSH is only available for running instances.`,
          );
          process.exit(1);
        }

        if (!d.host || !d.port) {
          printError("No SSH connection info available for this deployment.");
          process.exit(1);
        }

        const sshHost = d.host;
        const sshPort = String(d.port);
        const sshUser = "root";

        printInfo(`Connecting to ${sshUser}@${sshHost}:${sshPort}...`);

        const child = spawn(
          "ssh",
          ["-o", "StrictHostKeyChecking=no", "-p", sshPort, `${sshUser}@${sshHost}`],
          { stdio: "inherit" },
        );

        child.on("exit", (code) => {
          process.exit(code || 0);
        });
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
