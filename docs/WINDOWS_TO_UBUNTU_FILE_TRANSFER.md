# Windows 11 to Ubuntu Server File Transfer Guide

**Purpose**: Step-by-step instructions for copying files from a Windows 11 machine to the ES Inventory Hub Ubuntu server.

**Server Information:**
- **Hostname**: `goldberry`
- **User**: `rene`
- **Project Path**: `/opt/es-inventory-hub`
- **Target Directory**: `/opt/es-inventory-hub/docs/`

---

## Method 1: WinSCP (Recommended - GUI Tool)

**Best for**: Visual file management, drag-and-drop interface

### Step 1: Download and Install WinSCP
1. Download WinSCP from: https://winscp.net/eng/download.php
2. Install WinSCP on your Windows 11 machine
3. Launch WinSCP

### Step 2: Create New Session
1. Click **"New Session"** button
2. **File Protocol**: Select `SFTP`
3. **Host name**: Enter the server IP address or hostname (e.g., `192.168.99.246` or `goldberry`)
4. **Port number**: `22` (default SSH port)
5. **User name**: `rene`
6. **Password**: Enter your SSH password (or use key file - see Step 3)

### Step 3: Authentication Options

**Option A: Password Authentication**
- Enter your password in the password field
- Click **"Save"** to save the session

**Option B: Key File Authentication (More Secure)**
1. Click **"Advanced"** button
2. Go to **"SSH"** → **"Authentication"**
3. Click **"..."** next to **"Private key file"**
4. Browse to your private key file (e.g., `id_rsa` or `id_ed25519`)
5. Click **"OK"** and **"Save"**

### Step 4: Connect to Server
1. Select your saved session
2. Click **"Login"**
3. Accept the host key if prompted (first time only)

### Step 5: Copy Files
1. **Left Panel**: Navigate to your Windows `docs` directory
2. **Right Panel**: Navigate to `/opt/es-inventory-hub/docs/` on the server
3. **Select files** in the left panel (or select entire `docs` folder)
4. **Drag and drop** from left to right, OR
5. **Right-click** → **"Copy"** → **"Copy to..."** → Select destination

### Step 6: Verify Transfer
- Check that files appear in the right panel
- Verify file sizes match

---

## Method 2: PowerShell SCP (Command Line)

**Best for**: Quick transfers, automation, command-line users

### Step 1: Open PowerShell on Windows 11
- Press `Win + X` → Select **"Windows PowerShell"** or **"Terminal"**
- Or search for "PowerShell" in Start menu

### Step 2: Navigate to Source Directory
```powershell
cd C:\path\to\your\docs\directory
```

### Step 3: Copy Entire Directory
```powershell
scp -r . rene@goldberry:/opt/es-inventory-hub/docs/
```

**Or if using IP address:**
```powershell
scp -r . rene@192.168.99.246:/opt/es-inventory-hub/docs/
```

### Step 4: Copy Specific Files
```powershell
scp filename.md rene@goldberry:/opt/es-inventory-hub/docs/
```

### Step 5: Using SSH Key (If configured)
```powershell
scp -i C:\path\to\your\private_key -r . rene@goldberry:/opt/es-inventory-hub/docs/
```

**Note**: You'll be prompted for your password unless using key authentication.

---

## Method 3: FileZilla (Alternative GUI Tool)

**Best for**: Users familiar with FTP clients

### Step 1: Download and Install FileZilla
1. Download from: https://filezilla-project.org/download.php?type=client
2. Install FileZilla Client

### Step 2: Create New Site
1. Click **"File"** → **"Site Manager"**
2. Click **"New Site"**
3. **Protocol**: Select `SFTP - SSH File Transfer Protocol`
4. **Host**: Enter server IP or hostname
5. **Port**: `22`
6. **Logon Type**: `Normal` or `Key file`
7. **User**: `rene`
8. **Password**: Enter password (or browse to key file)
9. Click **"Connect"**

### Step 3: Transfer Files
1. **Left Panel**: Local site (your Windows files)
2. **Right Panel**: Remote site (server files)
3. Navigate to `/opt/es-inventory-hub/docs/` on remote side
4. Select files/folders and drag from left to right

---

## Method 4: WSL (Windows Subsystem for Linux)

**Best for**: Users with WSL installed, familiar with Linux commands

### Step 1: Open WSL Terminal
- Open **"Ubuntu"** or your Linux distribution from Start menu
- Or type `wsl` in PowerShell

### Step 2: Navigate to Windows Directory
```bash
cd /mnt/c/path/to/your/docs/directory
```

### Step 3: Use SCP or RSYNC
```bash
# Using SCP
scp -r . rene@goldberry:/opt/es-inventory-hub/docs/

# Using RSYNC (more efficient for large transfers)
rsync -avz . rene@goldberry:/opt/es-inventory-hub/docs/
```

---

## Method 5: Git (If Files Are in a Repository)

**Best for**: Version-controlled files, collaborative workflows

### Step 1: On Windows Machine
```powershell
cd C:\path\to\your\repository
git add docs/
git commit -m "Update docs directory"
git push origin main
```

### Step 2: On Ubuntu Server
```bash
cd /opt/es-inventory-hub
git pull origin main
```

**Note**: This method requires the files to be in a Git repository and both machines to have access to the same repository.

---

## Troubleshooting

### Connection Issues

**Problem**: "Connection refused" or "Connection timed out"
- **Solution**: Verify SSH service is running on server: `sudo systemctl status ssh`
- Check firewall rules allow port 22
- Verify server IP address/hostname is correct

**Problem**: "Permission denied"
- **Solution**: Verify you have write permissions: `ls -la /opt/es-inventory-hub/docs/`
- May need to use `sudo` or adjust permissions

**Problem**: "Host key verification failed"
- **Solution**: Remove old host key from `~/.ssh/known_hosts` on Windows
- Or accept new host key when prompted

### File Permission Issues

**On Ubuntu Server** (if needed):
```bash
# Check current permissions
ls -la /opt/es-inventory-hub/docs/

# Fix ownership if needed
sudo chown -R rene:rene /opt/es-inventory-hub/docs/

# Fix permissions if needed
chmod -R 644 /opt/es-inventory-hub/docs/
find /opt/es-inventory-hub/docs/ -type d -exec chmod 755 {} \;
```

### Large File Transfers

**For large directories**, use `rsync` instead of `scp`:
```bash
# On Windows (via WSL or PowerShell with rsync installed)
rsync -avz --progress docs/ rene@goldberry:/opt/es-inventory-hub/docs/
```

**Benefits of rsync**:
- Resumes interrupted transfers
- Only transfers changed files
- Shows progress
- More efficient for large datasets

---

## Quick Reference Commands

### From Windows PowerShell:
```powershell
# Copy entire docs directory
scp -r C:\path\to\docs rene@goldberry:/opt/es-inventory-hub/

# Copy single file
scp C:\path\to\file.md rene@goldberry:/opt/es-inventory-hub/docs/

# Copy with verbose output
scp -v -r C:\path\to\docs rene@goldberry:/opt/es-inventory-hub/docs/
```

### From WSL:
```bash
# Copy entire directory
scp -r /mnt/c/path/to/docs rene@goldberry:/opt/es-inventory-hub/

# Using rsync (recommended for large transfers)
rsync -avz --progress /mnt/c/path/to/docs/ rene@goldberry:/opt/es-inventory-hub/docs/
```

---

## Security Best Practices

1. **Use SSH Keys Instead of Passwords**
   - Generate key pair: `ssh-keygen -t ed25519`
   - Copy public key to server: `ssh-copy-id rene@goldberry`
   - Use private key in WinSCP/FileZilla

2. **Verify Server Identity**
   - Always verify host key fingerprint on first connection
   - Don't skip host key verification warnings

3. **Use SFTP (Not FTP)**
   - SFTP encrypts data in transit
   - Never use unencrypted FTP

4. **Limit Access**
   - Use firewall rules to restrict SSH access
   - Consider using non-standard SSH port (not recommended for beginners)

---

## Recommended Method

**For most users**: **WinSCP** (Method 1) is recommended because:
- ✅ Easy-to-use graphical interface
- ✅ Drag-and-drop functionality
- ✅ Visual file comparison
- ✅ Resume interrupted transfers
- ✅ Built-in text editor for quick edits

**For advanced users**: **PowerShell SCP** (Method 2) or **WSL rsync** (Method 4) for:
- ✅ Automation and scripting
- ✅ Faster transfers for large files
- ✅ Command-line workflow integration

---

**Version**: v1.20.1  
**Last Updated**: November 11, 2025 00:33 UTC  
**Maintainer**: ES Inventory Hub Team


