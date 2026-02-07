import { Command } from "commander";
import {
  loadConfig,
  getConfigValue,
  setConfigValue,
  resetConfig,
} from "../lib/config-manager.js";
import { printSuccess, printError, printKeyValue, printJson } from "../lib/output.js";

export function registerConfigCommand(program: Command) {
  const config = program.command("config").description("Manage CLI configuration");

  config
    .command("get <key>")
    .description("Get a config value")
    .action((key) => {
      const json = program.opts().json;
      const value = getConfigValue(key);
      if (value === undefined) {
        if (json) {
          printJson({ key, value: null });
        } else {
          printError(`Unknown config key: ${key}`);
        }
        return;
      }
      if (json) {
        printJson({ key, value });
      } else {
        console.log(value);
      }
    });

  config
    .command("set <key> <value>")
    .description("Set a config value")
    .action((key, value) => {
      const json = program.opts().json;
      setConfigValue(key, value);
      if (json) {
        printJson({ success: true, key, value });
      } else {
        printSuccess(`Set ${key} = ${value}`);
      }
    });

  config
    .command("list")
    .description("Show all config values")
    .action(() => {
      const json = program.opts().json;
      const cfg = loadConfig();
      if (json) {
        printJson(cfg);
      } else {
        printKeyValue(cfg as unknown as Record<string, string>);
      }
    });

  config
    .command("reset")
    .description("Reset config to defaults")
    .action(() => {
      const json = program.opts().json;
      resetConfig();
      if (json) {
        printJson({ success: true });
      } else {
        printSuccess("Config reset to defaults.");
      }
    });
}
