import { Command } from "commander";
import { printBanner } from "./lib/branding.js";
import { registerAuthCommand } from "./commands/auth.js";
import { registerHealthCommand } from "./commands/health.js";
import { registerConfigCommand } from "./commands/config.js";
import { registerComputeCommand } from "./commands/compute.js";
import { registerDeployCommand } from "./commands/deploy.js";
import { registerInstancesCommand } from "./commands/instances.js";
import { registerSshKeysCommand } from "./commands/ssh-keys.js";
import { registerAiCommand } from "./commands/ai.js";
import { registerDbCommand } from "./commands/db.js";
import { registerStorageCommand } from "./commands/storage.js";
import { registerBillingCommand } from "./commands/billing.js";

const program = new Command();

program
  .name("polaris")
  .description("Polaris Cloud CLI — GPU compute at your fingertips")
  .version("0.1.0", "-v, --version")
  .option("-j, --json", "Output raw JSON (for scripting)")
  .option("--no-color", "Disable colored output")
  .option("--api-url <url>", "Override API endpoint")
  .hook("preAction", () => {
    if (program.opts().noColor) {
      process.env.NO_COLOR = "1";
    }
  });

// Register all commands
registerAuthCommand(program);
registerHealthCommand(program);
registerConfigCommand(program);
registerComputeCommand(program);
registerDeployCommand(program);
registerInstancesCommand(program);
registerSshKeysCommand(program);
registerAiCommand(program);
registerDbCommand(program);
registerStorageCommand(program);
registerBillingCommand(program);

// Default action (no subcommand) — print banner + help
program.action(() => {
  printBanner();
  program.outputHelp();
});

program.parseAsync(process.argv).catch((err) => {
  console.error(err);
  process.exit(1);
});
