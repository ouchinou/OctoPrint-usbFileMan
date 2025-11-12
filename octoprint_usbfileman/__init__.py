import os
import sys
import shutil
import hashlib
import flask
import datetime
import time
import octoprint.plugin
from octoprint.events import Events


class UsbfilemanPlugin(octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.AssetPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SimpleApiPlugin,
                       octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.StartupPlugin):

    ##~~ SettingsPlugin mixin

    def on_after_startup(self):
        try:
            os.makedirs(self._settings.get(["copyFolder"]))
        except Exception as e:
            if not os.path.isdir(self._settings.get(["copyFolder"])):
                self._logger.info("Exception while trying to create/check for the copyFolder target: "+str(e))

    def on_api_get(self, request):
        self._logger.info("usbfileman on_api_get triggered.  Request: "+str(request))
        resultMessage = ""
        newFiles = False
        dest = self._settings.get(["copyFolder"])
        
        # Validate and normalize destination path to prevent path injection
        try:
            dest = os.path.realpath(dest)
            if not os.path.isdir(dest):
                return flask.jsonify(result="ERROR: Destination folder does not exist or is not accessible: "+dest)
        except Exception as e:
            self._logger.error("Invalid destination path: "+str(e))
            return flask.jsonify(result="ERROR: Invalid destination path: "+str(e))

        for folderToCheck in self._settings.get(["watchFolders"]):
            # Validate and normalize source path to prevent path injection
            try:
                src = os.path.realpath(folderToCheck)
            except Exception as e:
                self._logger.error("Invalid watch folder path: "+str(e))
                resultMessage += (" --- ERROR: Invalid watch folder path: "+folderToCheck)
                continue
                
            if not os.path.exists(src):
                resultMessage += (" --- USB mount path does not exist: "+src)
                continue
            try:
                usbFiles = os.listdir(src)
                # self._logger.info(str(usbFiles))
            except Exception as e:
                self._logger.info("Could not list files in watchFolder; exception: "+str(e))
                resultMessage += (" --- Could not list files in watchFolder; exception: "+str(e))
                continue
                # return flask.jsonify(result="Could not list files in watchFolder; exception: "+str(e))

            try:
                for file_name in usbFiles:
                    # Skip files with path traversal attempts or invalid characters
                    if ".." in file_name or "/" in file_name or "\\" in file_name:
                        self._logger.warning("Skipping file with suspicious path: "+str(file_name))
                        continue
                    
                    # self._logger.info(str(file_name))
                    file_root, file_extension = os.path.splitext(file_name)
                    if (str(file_root).startswith("COPIED")):
                        self._logger.info("File already copied according to name: "+str(file_name))
                        continue
                    if (str(file_root).startswith("._")):
                        self._logger.info("File seems to be a Mac system file; skipping.  Filename : "+str(file_name))
                        continue
                    if (file_extension in self._settings.get(["copyFileTypes"])):
                        full_src_name = os.path.join(src, file_name)
                        full_dest_name = os.path.join(dest, file_name)
                        
                        # Verify paths are within expected directories (path traversal protection)
                        if not full_src_name.startswith(src) or not full_dest_name.startswith(dest):
                            self._logger.error("Path traversal attempt detected for file: "+file_name)
                            continue
                        
                        if not (os.path.isfile(full_dest_name)):
                            # Check available disk space before copying
                            try:
                                if hasattr(os, 'statvfs'):  # Unix/Linux
                                    stat = os.statvfs(dest)
                                    available_space = stat.f_bavail * stat.f_frsize
                                else:  # Windows
                                    import ctypes
                                    free_bytes = ctypes.c_ulonglong(0)
                                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dest), None, None, ctypes.pointer(free_bytes))
                                    available_space = free_bytes.value
                                
                                file_size = os.path.getsize(full_src_name)
                                
                                if available_space < file_size * 1.1:  # 10% safety margin
                                    self._logger.error("Insufficient disk space to copy "+file_name)
                                    resultMessage += (" --- ERROR: Insufficient disk space to copy "+file_name)
                                    continue
                            except Exception as e:
                                self._logger.warning("Could not check disk space: "+str(e))
                            
                            shutil.copy(full_src_name, dest)
                            self._logger.info("Copied "+file_name+" to uploads/USB folder.")
                            resultMessage += (" --- Copied "+file_name+" to uploads/USB folder.")
                            newFiles = True
                            if (self._settings.get(["fileAction"]) == "rename"):
                                copiedName = os.path.join(src, ("COPIED" + file_name))
                                os.rename(full_src_name, copiedName)
                                resultMessage += (" --- Renamed original file in watchFolder to: "+copiedName)
                        else:
                            # Compare file sizes first for performance
                            if os.path.getsize(full_src_name) != os.path.getsize(full_dest_name):
                                files_differ = True
                            else:
                                # Only compute MD5 if sizes match
                                with open(full_src_name, 'rb') as f_src:
                                    src_md5 = hashlib.md5(f_src.read()).hexdigest()
                                with open(full_dest_name, 'rb') as f_dest:
                                    dest_md5 = hashlib.md5(f_dest.read()).hexdigest()
                                files_differ = (src_md5 != dest_md5)
                            
                            if files_differ:
                                newDestName = os.path.join(dest, (file_root + "-" + str(datetime.datetime.now().strftime('%y-%m-%d_%H-%M')) + file_extension) )
                                
                                # Check available disk space before copying
                                try:
                                    if hasattr(os, 'statvfs'):  # Unix/Linux
                                        stat = os.statvfs(dest)
                                        available_space = stat.f_bavail * stat.f_frsize
                                    else:  # Windows
                                        import ctypes
                                        free_bytes = ctypes.c_ulonglong(0)
                                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dest), None, None, ctypes.pointer(free_bytes))
                                        available_space = free_bytes.value
                                    
                                    file_size = os.path.getsize(full_src_name)
                                    
                                    if available_space < file_size * 1.1:  # 10% safety margin
                                        self._logger.error("Insufficient disk space to copy "+file_name)
                                        resultMessage += (" --- ERROR: Insufficient disk space to copy "+file_name)
                                        continue
                                except Exception as e:
                                    self._logger.warning("Could not check disk space: "+str(e))
                                
                                shutil.copyfile(full_src_name, newDestName)
                                self._logger.info("Copied a new version of "+file_name+" to uploads/USB folder as " + newDestName)
                                resultMessage += (" --- Copied a new version of "+file_name+" to uploads/USB folder as " + newDestName)
                                newFiles = True
                                if (self._settings.get(["fileAction"]) == "rename"):
                                    copiedName = os.path.join(src, ("COPIED" + file_name))
                                    os.rename(full_src_name, copiedName)
                                    resultMessage += (" --- Renamed original file in watchFolder to: "+copiedName)
            except Exception as e:
                self._logger.info("Could not copy files to uploads/USB folder; exception: "+str(e))
                resultMessage += (" --- Could not copy files to uploads/USB folder; exception: "+str(e))
                continue
                # return flask.jsonify(result="Could not copy files to uploads/USB folder; exception: "+str(e)+" .  Results before exception: "+resultMessage)

        if (resultMessage == ""):
            resultMessage = "Nothing to do."
        if (newFiles):
            self._event_bus.fire(Events.UPDATED_FILES, dict(type="printables"))
        return flask.jsonify(result="Finished without error.  Results: "+resultMessage)


    def get_settings_defaults(self):
        return dict(watchFolders = ["/media/usb1/toprint", "/media/usb2/toprint", "/media/usb3/toprint", "/media/usb4/toprint"],
            copyFolder = "/home/pi/.octoprint/uploads/USB",
            fileAction = "rename",
            copyFileTypes = [".gcode", ".gco", ".g", ".stl"],
            userFeedback = "log"
        )

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/usbfileman.js"],
            css=["css/usbfileman.css"],
            less=["less/usbfileman.less"]
        )

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            usbfileman=dict(
                displayName="Usbfileman Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="MakerGear",
                repo="OctoPrint-usbFileMan",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/MakerGear/OctoPrint-usbFileMan/archive/{target_version}.zip"
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Usbfileman Plugin"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = UsbfilemanPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

