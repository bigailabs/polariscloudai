import chalk from "chalk";

export const POLARIS_ASCII = `
  ____       _            _
 |  _ \\ ___ | | __ _ _ __(_)___
 | |_) / _ \\| |/ _\` | '__| / __|
 |  __/ (_) | | (_| | |  | \\__ \\
 |_|   \\___/|_|\\__,_|_|  |_|___/
`;

export function printBanner() {
  console.log(chalk.hex("#2D5A47")(POLARIS_ASCII));
  console.log(
    chalk.dim("  Polaris Cloud CLI — GPU compute at your fingertips\n"),
  );
}

export function printVersion(version: string) {
  console.log(`Polaris CLI v${version}`);
}
