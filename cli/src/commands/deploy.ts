import { Command } from "commander";
import chalk from "chalk";
import { createClient } from "../lib/api-client.js";
import {
  printSuccess,
  printError,
  printKeyValue,
  printJson,
  printInfo,
} from "../lib/output.js";
import { createSpinner } from "../lib/spinner.js";
import { select, input, confirm } from "../lib/prompts.js";
import { PolarisApiError } from "../lib/errors.js";
import type { Template } from "../lib/types.js";

export function registerDeployCommand(program: Command) {
  program
    .command("deploy")
    .description("Deploy a new instance (interactive or with flags)")
    .option("--template <id>", "Template ID (e.g., ollama, jupyter)")
    .option("--name <name>", "Deployment name")
    .option("--gpu <type>", "GPU type filter (for display only)")
    .option("--region <region>", "Region (for display only)")
    .option("-y, --yes", "Skip confirmation")
    .action(async (opts) => {
      const json = program.opts().json;

      try {
        const client = createClient(program.opts().apiUrl);

        // Fetch available templates
        const spinner = createSpinner("Loading templates...");
        spinner.start();
        const templates = await client.listTemplates();
        spinner.stop();

        const templateList = Object.values(templates);

        if (templateList.length === 0) {
          printError("No templates available.");
          process.exit(1);
        }

        // Select template
        let templateId = opts.template;
        if (!templateId) {
          templateId = await select({
            message: "Select a template to deploy:",
            choices: templateList.map((t: Template) => ({
              name: `${t.icon} ${t.name} — ${t.description.slice(0, 60)}...`,
              value: t.id,
            })),
          });
        }

        const template = templates[templateId];
        if (!template) {
          printError(`Template "${templateId}" not found.`);
          process.exit(1);
        }

        // Get deployment name
        let name = opts.name;
        if (!name) {
          name = await input({
            message: "Deployment name:",
            default: `${template.id}-${Date.now().toString(36).slice(-4)}`,
            validate: (v) =>
              /^[a-zA-Z0-9_-]+$/.test(v) || "Only letters, numbers, hyphens, underscores",
          });
        }

        // Collect parameters
        const params: Record<string, any> = {};
        for (const param of template.parameters) {
          if (param.options && param.options.length > 0) {
            params[param.name] = await select({
              message: `${param.label}:`,
              choices: param.options.map((o) => ({
                name: o.label,
                value: o.value,
              })),
              default: param.default,
            });
          } else if (param.type === "number") {
            const val = await input({
              message: `${param.label}:`,
              default: param.default !== undefined ? String(param.default) : undefined,
            });
            params[param.name] = parseInt(val, 10);
          } else {
            params[param.name] = await input({
              message: `${param.label}:`,
              default: param.default !== undefined ? String(param.default) : undefined,
            });
          }
        }

        // Confirmation
        if (!opts.yes) {
          console.log();
          console.log(
            chalk.bold(`  ${template.icon} Deploying ${template.name}`),
          );
          printKeyValue({
            Template: template.id,
            Name: name,
            "Deploy Time": template.estimated_deploy_time,
            Access: template.access_type,
            ...Object.fromEntries(
              Object.entries(params).map(([k, v]) => [k, String(v)]),
            ),
          });
          console.log();

          const ok = await confirm({
            message: "Deploy now?",
            default: true,
          });
          if (!ok) {
            printInfo("Cancelled.");
            return;
          }
        }

        // Deploy
        const deploySpinner = createSpinner(
          `Deploying ${template.name}...`,
        );
        deploySpinner.start();

        const result = await client.createDeployment({
          template_id: templateId,
          name,
          parameters: params,
        });

        deploySpinner.stop();

        if (json) {
          printJson(result);
          return;
        }

        printSuccess(`Deployment created!`);
        console.log();

        if (result.deployment_id) {
          printKeyValue({
            "Deployment ID": result.deployment_id,
            Status: result.status || "pending",
          });
        }

        if (result.access_url) {
          console.log();
          printInfo(`Access URL: ${chalk.underline(result.access_url)}`);
        }

        console.log();
        printInfo(
          `Track progress: ${chalk.dim("polaris instances get " + (result.deployment_id || name))}`,
        );
      } catch (err) {
        printError(
          err instanceof PolarisApiError
            ? err.toUserMessage()
            : String(err),
        );
        process.exit(1);
      }
    });
}
