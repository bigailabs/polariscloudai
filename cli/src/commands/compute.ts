import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import {
  printTable,
  printJson,
  printKeyValue,
  printError,
} from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { PolarisApiError } from "../lib/errors.js";

export function registerComputeCommand(program: Command) {
  const compute = program
    .command("compute")
    .description("Browse available compute resources and templates");

  compute
    .command("templates")
    .description("List available deployment templates")
    .action(async () => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching templates...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const templates = await client.listTemplates();
        spinner.stop();

        if (json) {
          printJson(templates);
          return;
        }

        const rows = Object.values(templates).map((t) => [
          t.icon + " " + t.id,
          t.name,
          t.category,
          t.estimated_deploy_time,
          t.access_type,
        ]);

        printTable(
          ["ID", "Name", "Category", "Deploy Time", "Access"],
          rows,
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

  compute
    .command("get <templateId>")
    .description("Show template details")
    .action(async (templateId) => {
      const json = program.opts().json;
      const spinner = createSpinner("Fetching template...");
      spinner.start();

      try {
        const client = createClient(program.opts().apiUrl);
        const template = await client.getTemplate(templateId);
        spinner.stop();

        if (json) {
          printJson(template);
          return;
        }

        console.log(
          `\n${template.icon} ${chalk.bold(template.name)}\n`,
        );
        printKeyValue({
          ID: template.id,
          Category: template.category,
          "Deploy Time": template.estimated_deploy_time,
          Access: template.access_type,
          Port: String(template.default_port),
        });
        console.log(`\n${chalk.dim("Description:")} ${template.description}`);
        console.log(
          `\n${chalk.dim("Features:")}\n${template.features.map((f) => `  • ${f}`).join("\n")}`,
        );
        if (template.parameters.length > 0) {
          console.log(`\n${chalk.dim("Parameters:")}`);
          for (const p of template.parameters) {
            const req = p.required ? chalk.red("*") : "";
            const def = p.default !== undefined ? chalk.dim(` (default: ${p.default})`) : "";
            console.log(`  ${p.name}${req} — ${p.label}${def}`);
          }
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

  compute
    .command("pricing")
    .description("Show GPU pricing reference")
    .action(async () => {
      const json = program.opts().json;

      const pricing = [
        ["RTX 3060", "12 GB", "$0.25/hr", "$150/mo"],
        ["RTX 3080", "10 GB", "$0.45/hr", "$270/mo"],
        ["RTX 3090", "24 GB", "$0.55/hr", "$330/mo"],
        ["RTX 4070", "12 GB", "$0.40/hr", "$240/mo"],
        ["RTX 4080", "16 GB", "$0.65/hr", "$390/mo"],
        ["RTX 4090", "24 GB", "$0.85/hr", "$510/mo"],
        ["A100 40GB", "40 GB", "$1.50/hr", "$900/mo"],
        ["A100 80GB", "80 GB", "$2.00/hr", "$1200/mo"],
        ["H100", "80 GB", "$3.50/hr", "$2100/mo"],
      ];

      if (json) {
        printJson(
          pricing.map(([gpu, vram, hourly, monthly]) => ({
            gpu,
            vram,
            hourly,
            monthly,
          })),
        );
        return;
      }

      printTable(["GPU", "VRAM", "Hourly", "Monthly"], pricing);
      console.log(
        chalk.dim("\n  Prices are estimates. Actual pricing depends on availability.\n"),
      );
    });

  compute
    .command("regions")
    .description("List available regions")
    .action(async () => {
      const json = program.opts().json;

      const regions = [
        ["lagos", "Lagos, Nigeria", "●", "Verda"],
        ["helsinki", "Helsinki, Finland", "●", "Hetzner"],
      ];

      if (json) {
        printJson(
          regions.map(([id, name, status, provider]) => ({
            id,
            name,
            status: "available",
            provider,
          })),
        );
        return;
      }

      printTable(
        ["Region", "Location", "Status", "Provider"],
        regions.map(([id, name, _status, provider]) => [
          id,
          name,
          chalk.green("● available"),
          provider,
        ]),
      );
    });
}
