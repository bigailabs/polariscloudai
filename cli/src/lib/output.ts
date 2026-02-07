import chalk from "chalk";
import Table from "cli-table3";

const forest = chalk.hex("#2D5A47");
const fern = chalk.hex("#4A7C59");
const copper = chalk.hex("#B87333");

export function printSuccess(message: string) {
  console.log(fern("✓") + " " + message);
}

export function printError(message: string) {
  console.error(chalk.red("✗") + " " + message);
}

export function printWarning(message: string) {
  console.log(copper("!") + " " + message);
}

export function printInfo(message: string) {
  console.log(chalk.dim("→") + " " + message);
}

export function printKeyValue(pairs: Record<string, string | number | null | undefined>) {
  const maxKeyLen = Math.max(...Object.keys(pairs).map((k) => k.length));
  for (const [key, value] of Object.entries(pairs)) {
    const paddedKey = key.padEnd(maxKeyLen);
    console.log(`  ${chalk.dim(paddedKey)}  ${value ?? chalk.dim("—")}`);
  }
}

export function printTable(
  headers: string[],
  rows: (string | number)[][],
) {
  const table = new Table({
    head: headers.map((h) => forest(h)),
    style: { head: [], border: ["dim"] },
    chars: {
      top: "─",
      "top-mid": "┬",
      "top-left": "┌",
      "top-right": "┐",
      bottom: "─",
      "bottom-mid": "┴",
      "bottom-left": "└",
      "bottom-right": "┘",
      left: "│",
      "left-mid": "├",
      mid: "─",
      "mid-mid": "┼",
      right: "│",
      "right-mid": "┤",
      middle: "│",
    },
  });

  for (const row of rows) {
    table.push(row.map(String));
  }

  console.log(table.toString());
}

export function printJson(data: unknown) {
  console.log(JSON.stringify(data, null, 2));
}
