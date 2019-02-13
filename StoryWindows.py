#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inspired by: 
ZetCode wxPython tutorial
www.zetcode.com
"""

import wx
import util
from util import *
from XML_write import *


ID_MENU_PHOTO = wx.NewId()
ID_MENU_CHANGE_DATE = wx.NewId()
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
        updateFolder(files_path)
        print("imgs_folder", imgs_folder)
        print("util.imgs_folder", util.imgs_folder)
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

        saveTool = self.toolbar.AddTool(wx.ID_SAVE, 'Save', saveIcon, shortHelp="Save entry.")
        self.photoTool = self.toolbar.AddCheckTool(ID_MENU_PHOTO, 'Photo', photoIcon, shortHelp="Change to photo mode.")
        changeDateTool = self.toolbar.AddTool(ID_MENU_CHANGE_DATE, 'Change', calendarIcon, shortHelp="Choose another date and time.")
        changeDir = self.toolbar.AddTool(ID_MENU_CHOOSE_DIR, 'Dir', folderIcon, shortHelp="Change directory.")
        importTool = self.toolbar.AddTool(ID_MENU_IMPORT, 'Import', importIcon, shortHelp="Import text or images from old version.")
        self.toolbar.AddSeparator()

        self.toolbar.Realize()


        self.Bind(wx.EVT_TOOL, self.OnSave, saveTool)
        self.Bind(wx.EVT_TOOL, self.OnPhoto, self.photoTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeDate, changeDateTool)
        self.Bind(wx.EVT_TOOL, self.OnChangeDir, changeDir)
        self.Bind(wx.EVT_TOOL, self.OnImport, importTool)


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
        self.vbox.Add(self.hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

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
        self.vbox.Add(hbox3, proportion=1, flag=wx.LEFT|wx.RIGHT|wx.EXPAND, border=10)

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
        text_shown = 'Ok bla bal \n sldfkj \n fuck that\nOk bla bal \n sldfkj \n fuck that\nOk bla bal \n sldfkj \n fuck that\n'
        self.fix_text_box = wx.StaticText(self.main_panel, label = text_shown, style = wx.TE_MULTILINE, size = (-1, 190))
        self.hbox4.Add(self.fix_text_box, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.vbox.Add(self.hbox4, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)

        self.vbox.Add((-1, 25))

        # Buttons
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        btn1 = wx.Button(self.main_panel, ID_CLICK_OK_BUTTON, label='Save', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnOKButtonClick, id=ID_CLICK_OK_BUTTON)
        hbox5.Add(btn1)
        btn2 = wx.Button(self.main_panel, ID_CLICK_BUTTON, label='Close', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.OnButtonClick, id=ID_CLICK_BUTTON)
        hbox5.Add(btn2, flag=wx.LEFT|wx.BOTTOM, border=5)
        self.vbox.Add(hbox5, flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)

        self.main_panel.SetSizer(self.vbox)

        
        self.updateLastEntryText()

    def setImg(self, name):
        self.bmp_shown = getImageToShow(name)
        self.img.SetBitmap(self.bmp_shown)

    def OnSave(self, e):
        self.OnOKButtonClick(e)
        print("saveTool clicked")

    def OnPhoto(self, e):
        textStr = self.input_text_field.GetValue()
        if textStr != ""  or self.imgLoaded == True:
            if self.imgLoaded == True:
                addstring = ', the loaded image'
            else:
                addstring = ''
            tog = self.photoTool.IsToggled()
            dial = wx.MessageDialog(None, 'If you change mode, the text' + addstring + ' and the chosen time will be lost. Do you want to proceed?', 'Warning',
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            dial.SetYesNoLabels('Fuck yeah!', 'No fucking way!')
            ans = dial.ShowModal()
            if ans == wx.ID_NO:
                self.toolbar.ToggleTool(ID_MENU_PHOTO, not tog)
                return
            elif ans == wx.ID_YES:
                self.removeWrittenText()
            else:
                print("WTF")

        if self.image_drop_space.IsShown():
            self.removeImg()
            self.imgLoaded = False
            self.image_drop_space.Hide()
        else:
            self.image_drop_space.Show()
        self.setDateNow()
        self.main_panel.Layout()
        print("photoTool clicked")

    def OnButtonClick(self, e):
        print("Close Button clicked")
        self.OnQuit(e)    

    def removeImg(self):
        self.fileDrop.loadedFile = None
        self.setImg(self.defaultImg)

    def OnOKButtonClick(self, e):
        print("OK Button clicked")
        textStr = self.input_text_field.GetValue()
        if textStr == "":
            wx.MessageBox("No fucking text!!", 'Info', wx.OK | wx.ICON_EXCLAMATION)
            return
        tog = self.photoTool.IsToggled()
        if tog:
            lf = self.fileDrop.loadedFile
            if lf is None:
                wx.MessageBox("No fucking image!!", 'Info', wx.OK | wx.ICON_EXCLAMATION)
                return
            curr_dat = self.cdDialog.dt
            copied_file_name = copyImgFileToImgsIfNotExistFull(lf, curr_dat)
            #uE = self.fileDrop.useExisting
            #ofn = self.fileDrop.newFileName
            #copied_file_name = copyImgFileToImgsIfNotExist(lf, uE, ofn)
            saveEntryInXml(textStr, curr_dat, "photo", copied_file_name)
            print("Hheeeifjsl", lf)
        else:
            saveEntryInXml(textStr, self.cdDialog.dt)
        
        self.removeImg()
        self.removeWrittenText()


    def removeWrittenText(self):
        self.input_text_field.Clear()
        self.updateDate(wx.DateTime.Now())

    def OnChangeDate(self, e):

        self.cdDialog.ShowModal()
        self.updateDate()

    def OnChangeDir(self, e):

        cdDiag = wx.DirDialog(None)
        cdDiag.ShowModal()
        files_path = cdDiag.GetPath()
        if files_path == "" or files_path is None:
            print("Null String")
            return
        updateFolder(files_path)
        createXMLandImgFolderIfNotExist(files_path)
        self.setDateNow()

    def OnImport(self, e):

        dial = wx.MessageDialog(None, 'Do you want to add images in a folder or text entries from a .txt file?', 'Question',
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
            cdDiag = wx.DirDialog(None, message = "Hooi", name = "Choose Location")
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
                    return     # the user changed their mind

                pathname = fileDialog.GetPath()
                try:
                    convertFromTxt(pathname)
                except IOError:
                    wx.LogError("Cannot open file '%s'." % newfile)
        self.setDateNow()

    def OnQuit(self, e):
        self.cdDialog.Destroy()
        self.Close()


    # Not quite working as intended
    #def Close(self):
    #    self.cdDialog.Destroy()
    #    super(Example, self).Close()

    def setDateNow(self):
        self.updateDate(wx.DateTime.Now())

    def updateDate(self, newDate = None):
        if newDate is not None:
            self.cdDialog.dt = newDate
        self.dateLabel.SetLabel('Date: ' + formDateTime(self.cdDialog.dt))
        self.fix_text_box.SetLabel('Hoooiii')
        self.updateLastEntryText()
    
    def updateLastEntryText(self):
        date_and_text = getLastXMLEntry(self.cdDialog.dt)
        next_date_and_text = getLastXMLEntry(self.cdDialog.dt, True)
        text_to_put = ""
        if date_and_text is not None:
            text_to_put += "Last entry was on " + formDateTime(date_and_text[0]) + "\n\n" + repNewlWithSpace(date_and_text[1]) + "\n\n"
        if next_date_and_text is not None:
            text_to_put += "Next entry is on " + formDateTime(next_date_and_text[0]) + "\n\n" + repNewlWithSpace(next_date_and_text[1])
        if text_to_put == "":
            text_to_put = "No older entry present."
        self.fix_text_box.SetLabel(text_to_put)
        self.vbox.Layout()

def main():
    testFolder = "C:\\Users\\Chrigi\\Desktop\\Neuer Ordner\\TestFolder"
    #addImgs(testFolder)
    #convertFromTxt(os.path.join(testFolder, "dummy_txt.txt"))
    app = wx.App()
    ex = Example(None)
    ex.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()