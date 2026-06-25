#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync, spawn } = require('child_process');

// ANSI color helpers
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  blue: '\x1b[34m'
};

function printBanner() {
  console.log(`${colors.cyan}${colors.bright}====================================================`);
  console.log(`🚀 RepoPilot CLI - Multi-Agent Software Engineer`);
  console.log(`====================================================${colors.reset}\n`);
}

// Locate the system Python
function findSystemPython() {
  const isWindows = process.platform === 'win32';
  const executables = isWindows ? ['python', 'python3', 'py'] : ['python3', 'python'];
  
  for (const exe of executables) {
    const result = spawnSync(exe, ['--version'], { encoding: 'utf8' });
    if (result.status === 0) {
      // Parse version
      const output = result.stdout || result.stderr || '';
      const match = output.match(/Python\s+(\d+)\.(\d+)/i);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        return { path: exe, major, minor, versionStr: output.trim() };
      }
    }
  }
  return null;
}

function setupVenv(systemPython, venvPath, requirementsPath, pkgVersion) {
  const isWindows = process.platform === 'win32';
  const venvPython = isWindows 
    ? path.join(venvPath, 'Scripts', 'python.exe')
    : path.join(venvPath, 'bin', 'python');
  const venvPip = isWindows
    ? path.join(venvPath, 'Scripts', 'pip.exe')
    : path.join(venvPath, 'bin', 'pip');
  
  const markerFile = path.join(venvPath, '.installed_version');
  
  // 1. Create venv if not exists
  if (!fs.existsSync(venvPython)) {
    console.log(`${colors.yellow}Creating local virtual environment at ${venvPath}...${colors.reset}`);
    fs.mkdirSync(path.dirname(venvPath), { recursive: true });
    
    const venvResult = spawnSync(systemPython, ['-m', 'venv', venvPath], { stdio: 'inherit' });
    if (venvResult.status !== 0) {
      console.error(`${colors.red}❌ Failed to create virtual environment.${colors.reset}`);
      console.error(`Please verify that python3-venv is installed on your system if you are running Linux (e.g. sudo apt install python3-venv).`);
      process.exit(1);
    }
    console.log(`${colors.green}✔ Virtual environment created successfully.${colors.reset}`);
  }

  // 2. Install / Update dependencies if version changed or marker missing
  let shouldInstall = true;
  if (fs.existsSync(markerFile)) {
    const installedVer = fs.readFileSync(markerFile, 'utf8').trim();
    if (installedVer === pkgVersion) {
      shouldInstall = false;
    }
  }

  if (shouldInstall) {
    console.log(`${colors.yellow}Installing/updating dependencies from requirements.txt...${colors.reset}`);
    console.log(`This might take a moment on first launch...`);
    
    // First, upgrade pip
    spawnSync(venvPip, ['install', '--upgrade', 'pip'], { stdio: 'inherit' });
    
    // Then install requirements
    const pipResult = spawnSync(venvPip, ['install', '-r', requirementsPath], { stdio: 'inherit' });
    
    if (pipResult.status !== 0) {
      console.error(`${colors.red}❌ Failed to install dependencies via pip.${colors.reset}`);
      process.exit(1);
    }
    
    // Write marker file
    fs.writeFileSync(markerFile, pkgVersion, 'utf8');
    console.log(`${colors.green}✔ Dependencies installed successfully.${colors.reset}`);
  }

  return venvPython;
}

function handleEnvFile() {
  const targetEnv = path.join(process.cwd(), '.env');
  if (!fs.existsSync(targetEnv)) {
    const sourceExample = path.join(__dirname, '..', '.env.example');
    if (fs.existsSync(sourceExample)) {
      console.log(`${colors.cyan}💡 No .env configuration file found in this directory.${colors.reset}`);
      console.log(`Creating a template .env file at ${targetEnv}...`);
      try {
        fs.copyFileSync(sourceExample, targetEnv);
        console.log(`${colors.green}✔ Template .env file created.${colors.reset}`);
        console.log(`${colors.yellow}👉 IMPORTANT: Please open the .env file in your editor and enter your DashScope, OpenAI, or Modal API keys.${colors.reset}\n`);
      } catch (err) {
        console.warn(`${colors.yellow}⚠️ Failed to copy .env.example: ${err.message}${colors.reset}`);
      }
    }
  }
}

function main() {
  printBanner();
  
  const packageJsonPath = path.join(__dirname, '..', 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  const pkgVersion = packageJson.version;
  
  // Find system python
  const pythonInfo = findSystemPython();
  if (!pythonInfo) {
    console.error(`${colors.red}❌ Python 3 was not found on your system.${colors.reset}`);
    console.error(`Please install Python 3.11 or later and ensure it is in your system PATH.`);
    process.exit(1);
  }
  
  // Check version requirements (Python 3.11+ is recommended, warn if < 3.10)
  if (pythonInfo.major !== 3 || pythonInfo.minor < 10) {
    console.warn(`${colors.yellow}⚠️ Warning: RepoPilot recommends Python 3.10+. Found version: ${pythonInfo.versionStr}${colors.reset}`);
  }
  
  // Define venv path in the user's home directory
  const venvPath = path.join(os.homedir(), '.repopilot', 'venv');
  const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
  
  // Set up venv and get venv python path
  const venvPython = setupVenv(pythonInfo.path, venvPath, requirementsPath, pkgVersion);
  
  // Ensure .env is handled in current workspace
  handleEnvFile();
  
  // Execute Python backend
  const runSwarmPath = path.join(__dirname, '..', 'run_swarm.py');
  const args = [runSwarmPath, ...process.argv.slice(2)];
  
  console.log(`${colors.green}Starting RepoPilot in: ${process.cwd()}...${colors.reset}\n`);
  
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8'
  };

  const child = spawn(venvPython, args, { 
    stdio: 'inherit',
    cwd: process.cwd(),
    env: env
  });
  
  child.on('close', (code) => {
    process.exit(code === null ? 1 : code);
  });
  
  child.on('error', (err) => {
    console.error(`${colors.red}❌ Error executing RepoPilot: ${err.message}${colors.reset}`);
    process.exit(1);
  });
}

main();
