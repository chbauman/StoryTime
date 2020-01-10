#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inspired by: 
ZetCode wxPython tutorial
www.zetcode.com
"""

import wx
import util
import shutil
from util import *
from XML_write import *

ID_MENU_PHOTO = wx.NewId()
ID_MENU_CHANGE_DATE = wx.NewId()
ID_MENU_SELFIE = wx.NewId()
ID_MENU_CHOOSE_DIR = wx.NewId()
ID_MENU_IMPORT = wx.NewId()
ID_CLICK_BUTTON = wx.NewId()
ID_CLICK_OK_BUTTON = wx.NewId()


class Example(wx.Frame):

    def __init__(self, *args, **kwargs):
        super(Example, self).__init__(*args, **kwargs)
        self.defaultImg = os.path.join(icon_path, "default_img.png")
        self.cdDialog = ChangeDateDialog(None, title='Change Date of entry')
        icon = wx.Icon()
        icon.CopyFromBitmap(wx.Bitmap(os.path.join(icon_path, "Entwurf.jpg"), wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)
        files_path = getInfoFromFile()
        update_folder(files_path)
        print("img_folder", img_folder)
        print("util.img_folder", util.img_folder)
        self.InitUI()
        self.SetSize((700, 600))
        self.SetTitle('Story Time')
        self.Center()

        self.imgLoaded = False

    def InitUI(self):

        self.count = 5

        # Toolbar
        iconSize = (50, 50)

        self.toolbar = self.CreateToolBar()
        self.toolbar.SetToolBitmapSize(iconSize)

        photoIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'photo_icon.png')), iconSize[0], iconSize[1])
        saveIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'save_icon.png')), iconSize[0], iconSize[1])
        calendarIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'calendar_icon.png')), iconSize[0], iconSize[1])
        folderIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'folder_icon.png')), iconSize[0], iconSize[1])
        importIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'import_icon.png')), iconSize[0], iconSize[1])
        selfieIcon = scale_bitmap(wx.Bitmap(os.path.join(icon_path, 'webcam_icon.png')), iconSize[0], iconSize[1])

        saveTool = self.toolbar.AddTool(wx.ID_SAVE, 'Save', saveIcon, shortHelp="Save entry.")
        self.photoTool = self.toolbar.AddCheckTool(ID_MENU_PHOTO, 'Photo', photoIcon, shortHelp="Change to photo mode.")
        changeDateTool = self.toolbar.AddTool(ID_MENU_CHANGE_DATE, 'Change', calendarIcon,
                                              shortHelp="Choose another date and time.")
        changeDir = self.toolbar.AddTool(ID_MENU_CHOOSE_DIR, 'Dir', folderIcon, shortHelp="Change directory.")
        importTool = self.toolbar.AddTool(ID_MENU_IMPORT, 'Import', importIcon,
                                          shortHelp="Import text or images from old version.")
        selfieTool = self.toolbar.AddTool(ID_MENU_SELFIE, 'Selfie', selfieIcon,
                                          shortHelp="Take a picture with your webcam.")
        self.toolbar.AddSeparator()

        self.toolbar.Realize()

        self.Bind(wx.EVT_TOOL, self.OnSave, saveTool)
        self.Bind(wx.EVT_TOOL, self.OnPhoto, self.photoTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeDate, changeDateTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeDir, changeDir)
        self.Bind(wx.EVT_TOOL, self.OnImport, importTool)
        self.Bind(wx.EVT_TOOL, self.OnSelfie, selfieTool)

        self.main_panel = wx.Panel(self)

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # Datum
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.dateLabel = wx.StaticText(self.main_panel, label='Date: ' + formDateTime(self.cdDialog.dt))
        self.dateLabel.SetFont(font)
        self.hbox1.Add(self.dateLabel, flag=wx.RIGHT, border=8)
        tc = wx.StaticText(self.main_panel)
        self.hbox1.Add(tc, proportion=1)
        self.vbox.Add(self.hbox1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=10)

        self.vbox.Add((-1, 10))

        # Text
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(self.main_panel, label='Input text below')
        st2.SetFont(font)
        hbox2.Add(st2)
        self.vbox.Add(hbox2, flag=wx.LEFT | wx.TOP, border=10)

        self.vbox.Add((-1, 10))

        # Text input field
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        self.input_text_field = wx.TextCtrl(self.main_panel, style=wx.TE_MULTILINE)
        hbox3.Add(self.input_text_field, proportion=1, flag=wx.EXPAND)
        self.vbox.Add(hbox3, proportion=1, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=10)

        self.vbox.Add((-1, 25))

        # Drop Target
        self.hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        self.bmp_shown = getImageToShow(self.defaultImg)
        self.img = wx.StaticBitmap(self.main_panel, -1, self.bmp_shown)
        self.image_drop_space = self.img
        self.image_drop_space.Hide()
        self.fileDrop = FileDrop(self.image_drop_space, self)
        self.image_drop_space.SetDropTarget(self.fileDrop)
        self.hbox4.Add(self.image_drop_space, proportion=0, flag=wx.ALL, border=5)

        # Bottom right text field
        text_shown = 'Default text.'
        self.fix_text_box = wx.StaticText(self.main_panel, label=text_shown, style=wx.TE_MULTILINE, size=(-1, 190))
        self.hbox4.Add(self.fix_text_box, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        self.vbox.Add(self.hbox4, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        self.vbox.Add((-1, 25))

        # Buttons
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        btn1 = wx.Button(self.main_panel, ID_CLICK_OK_BUTTON, label='Save', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnOKButtonClick, id=ID_CLICK_OK_BUTTON)
        hbox5.Add(btn1)
        btn2 = wx.Button(self.main_panel, ID_CLICK_BUTTON, label='Close', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnCloseButtonClick, id=ID_CLICK_BUTTON)
        hbox5.Add(btn2, flag=wx.LEFT | wx.BOTTOM, border=5)
        self.vbox.Add(hbox5, flag=wx.ALIGN_RIGHT | wx.RIGHT, border=10)

        self.main_panel.SetSizer(self.vbox)

        self.updateLastEntryText()

        self.Bind(wx.EVT_CLOSE, self.Cleanup)

    def setImg(self, name):
        """
        Sets an image in the preview panel in photo mode
        given the path of the image.
        """
        self.bmp_shown = getImageToShow(name)
        self.img.SetBitmap(self.bmp_shown)

    def set_img_with_date(self, curr_file, img_date):
        """
        Sets an image and updates the time.
        """
        self.updateDate(img_date)
        self.imgLoaded = True
        self.setImg(curr_file)

    def OnSave(self, e):
        """
        Same as the save button clicked.
        """
        self.OnOKButtonClick(e)

    def OnSelfie(self, e):
        """
        Opens dialog that shows the webcam and lets you take a picture
        with it which is added to the preview window then.
        """
        # Go to photo mode if not there yet
        if not self.photoTool.IsToggled():
            # Abort if canceled
            if self.OnPhoto(e) == -1:
                self.toolbar.ToggleTool(ID_MENU_PHOTO, False)
                return
            self.toolbar.ToggleTool(ID_MENU_PHOTO, True)

        # Show the dialog
        sDiag = SelfieDialog()
        sDiag.ShowModal()
        img = sDiag.taken_img

        # Save the image and show it in the preview
        if img is not None:
            curr_dt = wx.DateTime.Now()
            f_name = getImgBNameFromModTime(curr_dt) + "_Self.png"
            f_path = os.path.join(temp_folder, f_name)
            mkrid_if_not_exists(temp_folder)
            cv2.imwrite(f_path, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.set_img_with_date(f_path, curr_dt)
            self.fileDrop.loadedFile = f_path

        # Cleanup
        sDiag.Destroy()

    # Change to photo mode or back
    def OnPhoto(self, e):
        # If there is text in the textfield or an image loaded warn the user that it will be lost if he continues
        textStr = self.input_text_field.GetValue()
        if textStr != "" or self.imgLoaded == True:
            if self.imgLoaded == True:
                addstring = ', the loaded image'
            else:
                addstring = ''
            tog = self.photoTool.IsToggled()
            dial = wx.MessageDialog(None,
                                    'If you change mode, the text' + addstring + ' and the chosen time will be lost. Do you want to proceed?',
                                    'Warning',
                                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            dial.SetYesNoLabels('Fuck yeah!', 'No fucking way!')
            ans = dial.ShowModal()
            if ans == wx.ID_NO:
                # Toggle back
                self.toolbar.ToggleTool(ID_MENU_PHOTO, not tog)
                return -1
            elif ans == wx.ID_YES:
                self.removeWrittenText()
            else:
                print("WTF")

        # Toggle the showing of the Image (drop space)
        if self.image_drop_space.IsShown():
            self.removeImg()
            self.imgLoaded = False
            self.image_drop_space.Hide()
        else:
            self.image_drop_space.Show()

        # Update date and time and the layout
        self.setDateNow()
        self.main_panel.Layout()
        print("photoTool clicked")

    def OnCloseButtonClick(self, e):
        """
        Same as clicking X. Closes the application.
        """
        print("Close Button clicked")
        self.OnQuit(e)

    def removeImg(self):
        """
        Set the image in the image drop space to the default.
        """
        self.fileDrop.loadedFile = None
        self.setImg(self.defaultImg)
        self.imgLoaded = False

    def OnOKButtonClick(self, e):
        """
        Saves the text (and the photo in photo mode) in an 
        XML entry. Does nothing if text (or image in photo mode) is missing.
        """

        # Check if there is any text at all
        textStr = self.input_text_field.GetValue()
        if textStr == "":
            wx.MessageBox("No fucking text!!", 'Info', wx.OK | wx.ICON_EXCLAMATION)
            return

        # Check which mode is on
        tog = self.photoTool.IsToggled()
        if tog:

            # Check if there is an image
            lf = self.fileDrop.loadedFile
            if lf is None:
                wx.MessageBox("No fucking image!!", 'Info', wx.OK | wx.ICON_EXCLAMATION)
                return

            # Save image entry
            curr_dat = self.cdDialog.dt
            copied_file_name = copyImgFileToImgsIfNotExistFull(lf, curr_dat)
            saveEntryInXml(textStr, curr_dat, "photo", copied_file_name)
        else:
            saveEntryInXml(textStr, self.cdDialog.dt)

        # Clear the contents
        self.removeImg()
        self.removeWrittenText()

    def removeWrittenText(self):
        """
        Clear text field and update date and time to now.
        """
        self.input_text_field.Clear()
        self.updateDate(wx.DateTime.Now())

    def OnChangeDate(self, e):
        """
        Shows dialog that lets the user change the current date.
        """
        self.cdDialog.ShowModal()
        self.updateDate()

    def OnChangeDir(self, e):
        """
        Shows dialog that lets the user change the current 
        directory.
        """
        # Show dialog and get folder
        cdDiag = wx.DirDialog(None)
        cdDiag.ShowModal()
        files_path = cdDiag.GetPath()
        cdDiag.Destroy()

        # If none selected return
        if files_path == "" or files_path is None:
            print("No new folder selected.")
            return

        # Update and create data directories if not existing
        update_folder(files_path)
        createXMLandImgFolderIfNotExist(files_path)
        self.setDateNow()

    def OnImport(self, e):

        dial = wx.MessageDialog(None, 'Do you want to add images in a folder or text entries from a .txt file?',
                                'Question',
                                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.CANCEL_DEFAULT)
        dial.SetYesNoLabels('Text of course!', 'Fucking images!')
        imp_imgs = None
        ans = dial.ShowModal()
        if ans == wx.ID_NO:
            imp_imgs = True
        elif ans == wx.ID_YES:
            imp_imgs = False

        print("Fuck, ", imp_imgs)
        if imp_imgs is None:
            return

        if imp_imgs == True:
            cdDiag = wx.DirDialog(None, message="Hooi", name="Choose Location")
            cdDiag.ShowModal()
            files_path = cdDiag.GetPath()
            if files_path == "" or files_path is None:
                print("Null String")
                return
            addImgs(files_path)
        else:
            with wx.FileDialog(self, "Open Text file", wildcard="Text files (*.txt)|*.txt",
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return  # the user changed their mind

                pathname = fileDialog.GetPath()
                try:
                    convertFromTxt(pathname)
                except IOError:
                    wx.LogError("Cannot open file '%s'." % newfile)
        self.setDateNow()

    def OnQuit(self, e):
        """
        Closing the app, writes the working directory to file for next use,
        empties temp folder and closes the app.
        Should always be executed before closing the app.
        """
        self.cdDialog.Destroy()
        writeFolderToFile()
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
        self.Close()

        # Destroys the change date dialog that holds the date (This is ugly)

    # Is this even used???
    def Cleanup(self, e):
        print("Cleanup")
        self.cdDialog.Destroy()
        writeFolderToFile()
        self.Destroy()

    def setDateNow(self):
        """
        Updates the date and time to now.
        """
        self.updateDate(wx.DateTime.Now())

    def updateDate(self, newDate=None):
        """
        Updates the date to specified datetime. 
        Updates the static datetime text and looks
        for the most recent XML text entries for text preview.
        """
        if newDate is not None:
            self.cdDialog.dt = newDate
        self.dateLabel.SetLabel('Date: ' + formDateTime(self.cdDialog.dt))
        self.fix_text_box.SetLabel('Hoooiii')  # Probably unnecessary.
        self.updateLastEntryText()

    def updateLastEntryText(self):
        """
        Fills the static datetime text with the most recent entries
        for preview.
        """
        # Get most recent last and next XML text entries (if existing).
        date_and_text = getLastXMLEntry(self.cdDialog.dt)
        next_date_and_text = getLastXMLEntry(self.cdDialog.dt, True)

        # Construct the text to put into the preview panel.
        text_to_put = ""
        if date_and_text is not None:
            text_to_put += "Last entry was on " + formDateTime(date_and_text[0]) + "\n\n" + rep_newlines_with_space(
                date_and_text[1]) + "\n\n"
        if next_date_and_text is not None:
            text_to_put += "Next entry is on " + formDateTime(next_date_and_text[0]) + "\n\n" + rep_newlines_with_space(
                next_date_and_text[1])
        if text_to_put == "":
            text_to_put = "No older entry present."

        # Set text and update layout
        self.fix_text_box.SetLabel(text_to_put)
        self.vbox.Layout()


def main():
    """
    DOO ALLL THE STUFFFFFF.
    """
    app = wx.App()
    ex = Example(None)
    ex.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
