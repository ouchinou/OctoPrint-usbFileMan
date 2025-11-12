# OctoPrint-usbFileMan

A robust OctoPrint plugin for managing files from USB flash drives. Automatically detects, copies, and manages G-code files from USB drives to your OctoPrint uploads folder.

## Features

- 🔒 **Secure**: Path traversal protection and input validation
- 📁 **Smart Copying**: Compares file sizes before MD5 hash computation for better performance
- 💾 **Disk Space Check**: Verifies available space before copying (cross-platform)
- 🔄 **Duplicate Detection**: Uses MD5 hashing to detect modified files
- 📝 **File Tracking**: Marks copied files to avoid duplicates
- 🖥️ **Cross-Platform**: Works on Linux (Raspberry Pi) and Windows
- 🚫 **Mac-Friendly**: Automatically skips macOS system files (._* files)

## How It Works

When triggered (via API or automatic USB mount), the plugin:

1. Scans configured watch folders for G-code files
2. Validates file paths for security
3. Checks if files are new or have been modified (size comparison + MD5)
4. Verifies sufficient disk space is available
5. Copies new/modified files to the OctoPrint uploads folder
6. Optionally renames source files with "COPIED" prefix
7. Notifies OctoPrint to refresh the file list

Modified files are saved with a timestamp suffix (e.g., `model-25-11-12_14-30.gcode`) to preserve both versions.

## Setup

### Installation

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/ouchinou/OctoPrint-usbFileMan/archive/master.zip

### Raspberry Pi Configuration (Recommended)

The computer running OctoPrint needs to be configured to automatically mount USB flash drives.

**Requirements:**
- Raspberry Pi 3B/3B+ or newer
- OctoPi 0.15.1 or newer
- Python 3.7+

**Step 1: Configure Auto-Mount**

Follow these instructions: https://raspberrypi.stackexchange.com/a/66324

**Step 2: Trigger Plugin on USB Insert**

Edit `/usr/local/bin/cpmount` and add this line before the final `fi`:

```bash
sudo -u pi /home/pi/oprint/bin/octoprint client get '/api/plugin/usbfileman'
```

If you use multiple USB ports, add this line to each "else" statement, below the `/usr/bin/pmount` call.

**Step 3: Make Script Executable**

```bash
sudo chmod u+x /usr/local/bin/cpmount
```

**Step 4: Install NTFS Support (Optional)**

For NTFS-formatted drives:

```bash
sudo apt-get install ntfs-3g
```

## Configuration

Configure the plugin through OctoPrint's settings interface:

### Watch Folders
List of directories to monitor for new files. Default:
```
/media/usb1/toprint
/media/usb2/toprint
/media/usb3/toprint
/media/usb4/toprint
```

### Copy Destination
Where files will be copied to. Default:
```
/home/pi/.octoprint/uploads/USB
```

### File Action
What to do with source files after copying:
- **rename**: Prefix with "COPIED" (prevents re-copying)
- **leave**: Keep original filename (may re-copy on next scan)

### Supported File Types
File extensions to copy. Default:
```
.gcode, .gco, .g, .stl
```

### Configuration Example

In `config.yaml`:

```yaml
plugins:
  usbfileman:
    watchFolders:
      - /media/usb1/toprint
      - /media/usb2/toprint
    copyFolder: /home/pi/.octoprint/uploads/USB
    fileAction: rename
    copyFileTypes:
      - .gcode
      - .gco
      - .g
      - .stl
```

## API Usage

Trigger a manual scan:

```bash
curl -X GET http://octopi.local/api/plugin/usbfileman -H "X-Api-Key: YOUR_API_KEY"
```

## Security Features

This plugin implements several security measures:

- **Path Validation**: All paths are normalized with `os.path.realpath()` to prevent path traversal attacks
- **Path Traversal Detection**: Rejects files containing `..`, `/`, or `\` in filenames
- **Directory Boundaries**: Verifies all file operations stay within configured directories
- **Disk Space Verification**: Checks available space (with 10% safety margin) before copying
- **Safe File Handling**: Uses context managers to prevent file handle leaks

## Troubleshooting

### Files Not Copying

1. Check OctoPrint logs for error messages
2. Verify watch folder paths exist and are accessible
3. Ensure destination folder has write permissions
4. Check available disk space

### Permission Denied Errors

```bash
sudo chown -R pi:pi /home/pi/.octoprint/uploads/USB
sudo chmod -R 755 /home/pi/.octoprint/uploads/USB
```

### USB Not Detected

1. Verify auto-mount is configured correctly
2. Check `/usr/local/bin/cpmount` is executable
3. Test manual mount: `sudo pmount /dev/sda1`
4. Check system logs: `dmesg | tail`

## Changelog

### Version 0.1.3 (Upcoming)
- Added path traversal protection
- Improved performance with file size comparison before MD5
- Added disk space verification (cross-platform)
- Fixed memory leaks with proper file handle management
- Modernized code for Python 3
- Improved error handling and logging
- Fixed indentation issues

### Version 0.1.2
- Initial public release

## Support

For issues and feature requests, please visit:
https://github.com/ouchinou/OctoPrint-usbFileMan/issues

## License

Licensed under AGPLv3

## Credits

**Original Author**: Joshua Wills (MakerGear)  
**Fork Maintainer**: ouchinou  
**Recent Improvements**: Security hardening and performance optimization (2025)
