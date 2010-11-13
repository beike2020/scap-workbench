# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#      Maros Barabas        <mbarabas@redhat.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import pygtk
import gtk
import gobject
import pango

import abstract
import logging
import core
from events import EventObject

import commands
import filter
import render

from htmltextview import HtmlTextView
from threads import thread as threadSave


logger = logging.getLogger("OSCAPEditor")

class ItemList(abstract.List):

    def __init__(self, widget, core, progress=None, filter=None):
        self.core = core
        self.filter = filter
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, True)
        abstract.List.__init__(self, "gui:edit:item_list", core, widget)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:btn:menu:edit", "update", self.__update)
        #self.add_receiver("gui:btn:edit", "update", self.__update)
        self.add_receiver("gui:btn:edit:filter", "search", self.__search)
        self.add_receiver("gui:btn:edit:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:edit:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:edit:DHItemsTree", "filled", self.__filter_refresh)

        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.add_sender(self.id, "item_changed")

        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())

    def __update(self):
        self.get_TreeView().set_model(self.data_model.model)
        self.data_model.fill()
        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item_edit, self.get_TreeView()))
        self.core.force_reload_items = False

    def __search(self):
        self.search(self.filter.get_search_text(),1)
        
    def __filter_add(self):
        self.data_model.map_filter = self.filter_add(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_del(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_refresh(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))


    @threadSave
    def __cb_item_changed(self, widget, treeView):
        """Make all changes in application in separate threads: workaround for annoying
        blinking when redrawing treeView
        """
        gtk.gdk.threads_enter()
        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.core.selected_item_edit = model.get_value(iter, 0)
                self.emit("update")
        treeView.columns_autosize()
        gtk.gdk.threads_leave()

class MenuButtonEdit(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DataHandler(self.core)
        
        #draw body
        self.body = self.builder.get_object("edit:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        self.rules_list = ItemList(self.builder.get_object("edit:tw_items"), self.core, self.progress, self.filter)
        self.filter.expander.cb_changed()

        # set signals
        self.add_sender(self.id, "update")
        
        """Get widget for details
        """
        #main
        self.btn_revert = self.builder.get_object("edit:btn_revert")
        self.btn_save = self.builder.get_object("edit:btn_save")
        self.btn_item_remove = self.builder.get_object("edit:item:btn_remove")
        self.btn_item_add = self.builder.get_object("edit:item:btn_add")
        
        self.btn_revert.connect("clicked", self.__cb_revert)
        self.btn_save.connect("clicked", self.__cb_save)
        self.btn_item_remove.connect("clicked", self.__cb_item_remove)
        self.btn_item_add.connect("clicked", self.__cb_item_add)
        
        #general
        self.item_id = self.builder.get_object("edit:general:lbl_id")
        self.lv_version = self.builder.get_object("edit:general:lv_version")
        self.chbox_hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.chbox_prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.chbox_abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.entry_cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        
        ##status
        #self.lv_status = self.builder.get_object("edit:general:lv_status")
        #self.status_model = commands.DHEditStatus(self.core, self.lv_status)
        
        ##question
        #self.lv_question = self.builder.get_object("edit:general:lv_question")
        #self.guestion_model = commands.DHEditQuestion(self.core, self.lv_question)
        
        ##references
        #self.lv_reference = self.builder.get_object("edit:general:lv_reference")
        #self.ref_model = commands.DHEditReferences(self.core, self.lv_reference)
        
        ##rationale
        #self.lv_rationale = self.builder.get_object("edit:general:lv_rationale")
        #self.rationale_model = commands.DHEditRationale(self.core, self.lv_rationale)
        
        self.edit_title = EditTitle(self.core, self.builder)
        self.edit_description = EditDescription(self.core, self.builder)
        
        ##warning
        #self.lv_warning = self.builder.get_object("edit:general:lv_warning")
        #self.sw_warning = self.builder.get_object("edit:general:sw_warning")
        #self.warning_model = commands.DHEditWarning(self.core, self.lv_warning, self.sw_warning)
        
        ##extends
        #self.lbl_extends = self.builder.get_object("edit:dependencies:lbl_extends")
        
        ##Conflicts
        #self.lv_conflicts = self.builder.get_object("edit:dependencies:lv_conflicts")
        #self.conflict_model = commands.DHEditConflicts(self.core, self.lv_conflicts)
        
        #self.lv_reguires = self.builder.get_object("edit:dependencies:lv_reguires")
        #self.lv_platform = self.builder.get_object("edit:dependencies:lv_platform")
        #self.lv_ident = self.builder.get_object("edit:dependencies:lv_ident")
        
        #operations
        #self.chbox_selected = self.builder.get_object("edit:operations:chbox_selected")
        self.combo_severity = self.builder.get_object("edit:operations:combo_severity")
        self.entry_impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.lv_fixtext = self.builder.get_object("edit:operations:lv_fixtext")
        self.lv_fix = self.builder.get_object("edit:operations:lv_fix")
        self.lv_fix = self.builder.get_object("edit:operations:lv_check")
        
        #others
        self.chbox_multipl = self.builder.get_object("edit:other:chbox_multipl")
        self.combo_role = self.builder.get_object("edit:other:combo_role")
        self.lv_profile_note = self.builder.get_object("edit:other:lv_profile_note")
        
        #values
        self.tv_values = self.builder.get_object("edit:values:tv_values")
        self.btn_value_edit = self.builder.get_object("edit:values:btn_edit")
        self.btn_value_add = self.builder.get_object("edit:values:btn_add")
        self.btn_value_remove = self.builder.get_object("edit:values:btn_remove")
        
        self.btn_value_edit.connect("clicked", self.__cd_value_edit)
        self.btn_value_add.connect("clicked", self.__cd_value_add)
        self.btn_value_remove.connect("clicked", self.__cd_value_remove)

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:item_list", "changed", self.__update)
        
            
    def __cb_revert(self, widget):
        pass

    def __cb_save(self, widget):
        pass

    def __cb_item_remove(self, widget):
        pass

    def __cb_item_add(self, widget):
        pass

    def __cd_value_edit(self, widget):
        pass

    def __cd_value_add(self, widget):
        pass

    def __cd_value_remove(self, widget):
        pass

    def __update(self):

        details = self.data_model.get_item_objects(self.core.selected_item_edit)
        if details != None:
            self.item_id.set_text(details["id"])
            self.chbox_hidden.set_active(details["hidden"])
            self.chbox_prohibit.set_active(details["prohibit_changes"])
            self.chbox_abstract.set_active(details["abstract"])
            
            self.edit_title.fill(details["item"], details["titles"])
            self.edit_description.fill(details["item"], details["descriptions"])
            
            #self.ref_model.fill(details["references"])
            #self.guestion_model.fill(details["questions"])
            #self.status_model.fill(details["statuses"])
            #self.conflict_model.fill(details["conflicts"])
            #self.rationale_model.fill(details["rationale"])
            
            #self.warning_model.fill(details["warnings"])
            
            if details["cluster_id"] != None:
                self.entry_cluster_id.set_text(details["cluster_id"])
            else:
                self.entry_cluster_id.set_text("")

            if details["extends"] != None:
                self.lbl_extends.set_text(details["extends"])
            else:
                self.lbl_extends.set_text("")

            
            # dat only for rule
            if details["typetext"] == "Rule":
                self.entry_impact_metric.set_sensitive(True)
                if details["imapct_metric"] != None:
                    self.entry_impact_metric.set_text(details["imapct_metric"])
                else:
                    self.entry_impact_metric.set_text("")

                self.chbox_multipl.set_sensitive(True)
                self.chbox_multipl.set_active(details["multiple"])
                
                # clean data only group and set insensitive
            #data only for Group
            else:
                
                
                
                # clean data only for rule and set insensitive
                self.entry_impact_metric.set_sensitive(False)
                self.chbox_multipl.set_sensitive(False)
                self.entry_impact_metric.set_text("")
        else:
            return


class Edit_abs:
    
    def __init__(self, core, lv, values):
        self.core = core
        self.values = values
        self.item = None
        self.lv = lv
        self.model = lv.get_model()
        self.selection = lv.get_selection()
        self.selection.set_mode(gtk.SELECTION_SINGLE)
        
    def cb_edit_row(self, widget):
        (model,iter) = self.selection.get_selected()
        if iter:
            window = EditDialogWindow(self.item, self.core, self.values, new=False)
        else:
            self.dialogEditNotSelected()

    def cb_add_row(self, widget):
        window = EditDialogWindow(self.item, self.core, self.values, new=True)

    def cb_del_row(self, widget):
        iter = self.dialogEditDel()
        if iter != None:
            self.values["cb"](self.item, self.model, iter, None, None, True)

    def dialogEditDel(self):
        
        (model,iter) = self.selection.get_selected()
        if iter:
            md = gtk.MessageDialog(self.core.main_window, 
                gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO, "Do you want delete selected row?")
            md.set_title("Delete row")
            result = md.run()
            md.destroy()
            if result == gtk.RESPONSE_NO: 
                return None
            else: 
                return iter
        else:
            self.dialogInfo("Choose row which you want delete.")

    def dialogEditNotSelected(self):
        self.dialogInfo("Choose row which you want edit.")
        
        
    def dialogInfo(self, text):
        md = gtk.MessageDialog(self.core.main_window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, text)
        md.set_title("Info")
        md.run()
        md.destroy()

    def addColumn(self, name, column):
        txtcell = abstract.CellRendererTextWrap()
        column = gtk.TreeViewColumn(name, txtcell, text=column)
        column.set_resizable(True)
        self.lv.append_column(column)

class EditTitle(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_TEXT = 1
    COLUMN_OBJECT = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_title")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)

        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit title",
                        "view":         lv,
                        "cb":           self.DHEditTitle,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Title",
                                        "column":   self.COLUMN_TEXT,
                                        "empty":    False, 
                                        "unique":   False}
                        }
        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_title_add")
        btn_edit = builder.get_object("edit:general:btn_title_edit")
        btn_del = builder.get_object("edit:general:btn_title_del")
        
        # set callBack to btn
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)
        
        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Title",self.COLUMN_TEXT)
        
    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, (" ".join(data.text.split())), data])

class EditDescription(commands.DHEditItems,Edit_abs):

    COLUMN_LAN = 0
    COLUMN_DES = 1
    COLUMN_OBJECTS = 2

    def __init__(self, core, builder):

        #set listView and model
        lv = builder.get_object("edit:general:lv_description")
        model = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        lv.set_model(model)
        
        #information for new/edit dialog
        values = {
                        "name_dialog":  "Edit description",
                        "view":         lv,
                        "cb":           self.DHEditDescription,
                        "textEntry":    {"name":    "Language",
                                        "column":   self.COLUMN_LAN,
                                        "empty":    False, 
                                        "unique":   True},
                        "textView":     {"name":    "Description",
                                        "column":   self.COLUMN_DES,
                                        "empty":    False, 
                                        "unique":   False},
                        }

        Edit_abs.__init__(self, core, lv, values)
        btn_add = builder.get_object("edit:general:btn_description_add")
        btn_edit = builder.get_object("edit:general:btn_description_edit")
        btn_del = builder.get_object("edit:general:btn_description_del")
        
        # set callBack
        btn_add.connect("clicked", self.cb_add_row)
        btn_edit.connect("clicked", self.cb_edit_row)
        btn_del.connect("clicked", self.cb_del_row)

        self.addColumn("Language",self.COLUMN_LAN)
        self.addColumn("Description",self.COLUMN_DES)

    def fill(self, item, objects):
        self.item = item
        self.model.clear()
        if objects != []:
            for data in objects:
                self.model.append([data.lang, data.text, data])

class EditDialogWindow(EventObject):
    
    def __init__(self, item, core, values, new=True):
        
        self.core = core
        self.new = new
        self.values = values
        self.item = item
        builder = gtk.Builder()
        builder.add_from_file("/usr/share/scap-workbench/edit_item.glade")
        
        self.window = builder.get_object("dialog:edit_item")
        self.window.set_keep_above(True)
        self.window.connect("delete-event", self.__delete_event)
        
        btn_ok = builder.get_object("btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)
        
        #info for change
        self.iter_del = None

        table = builder.get_object("table")
        table.hide_all()
        table.show()
        
        self.selection = values["view"].get_selection()
        (self.model, self.iter) = self.selection.get_selected()

        if "textEntry" in values:
            self.textEntry = builder.get_object("entryText")
            self.textEntry.show_all()
            lbl_entryText = builder.get_object("lbl_entryText")
            lbl_entryText.set_label(values["textEntry"]["name"])
            lbl_entryText.show_all()
            if new == False:
                self.textEntry.set_text(self.model.get_value(self.iter,values["textEntry"]["column"]))
                

        if "textView" in values:
            self.textView = builder.get_object("textView")
            sw_textView = builder.get_object("sw_textView")
            sw_textView.show_all()
            lbl_textView = builder.get_object("lbl_textView")
            lbl_textView.set_label(values["textView"]["name"])
            lbl_textView.show()
            if new == False:
                buff = self.textView.get_buffer()
                buff.set_text(self.model.get_value(self.iter,values["textView"]["column"]))

        if "cbEntry" in values:
            cbEntry = builder.get_object("cbEntry")
            lbl_cbEntry = builder.get_object("lbl_cbEntry")
            cbEntry.show_all()
            lbl_cbEntry.show()
            if new == False:
                logger.info("not implemented all yet")
                

        self.window.show()

    def __cb_do(self, widget):
        
        if self.new == True:
            dest_path = None
            self.iter = None
        else:
            dest_path = self.iter
        
        if "textEntry" in self.values:
            text_textEntry = self.textEntry.get_text()
            
            # if data should not be empty and control
            if self.values["textEntry"]["empty"] == False:
                if not self.control_empty(text_textEntry, self.values["textEntry"]["name"]):
                    return
            
            # if data sould be unique and control
            if self.values["textEntry"]["unique"] == True:
                path = self.control_unique(self.values["textEntry"]["name"], self.model, 
                                            self.values["textEntry"]["column"], text_textEntry, self.iter)
                if path == False:
                    return
                else:
                    dest_path = path
                    
        if "textView" in self.values:
            buff = self.textView.get_buffer()
            iter_start = buff.get_start_iter()
            iter_end = buff.get_end_iter()
            text_textView = buff.get_text(iter_start, iter_end, True)
            
            # if data should not be empty and control
            if self.values["textView"]["empty"] == False:
                if not self.control_empty(text_textView, self.values["textView"]["name"]):
                    return

            # if data sould be unique and control
            if self.values["textView"]["unique"] == True:
                path = self.control_unique(self.values["textView"]["name"], self.model, 
                                            self.values["textView"]["column"], text_textView, self.iter)
                if path == False:
                    return
                else:
                    dest_path = path
        
        # new row and unique => add new row
        if dest_path == None:
            iter = self.model.append()
            self.selection.select_path(self.model.get_path(iter))
            self.values["cb"](self.item, self.model, iter, None, text_textEntry)
        
        # edit row
        else:
            iter = self.model.get_iter(dest_path)
            if self.iter and dest_path != self.model.get_path(self.iter):
                self.values["cb"](self.item, self.model, self.iter, None, None, True)

        # if insert data are correct, put them to the model
        if "textEntry" in self.values:
            self.model.set_value(iter,self.values["textEntry"]["column"], text_textEntry)
            self.values["cb"](self.item, self.model, iter, self.values["textEntry"]["column"], text_textEntry)
                    
        if "textView" in self.values:
            self.model.set_value(iter,self.values["textView"]["column"], text_textView)
            self.values["cb"](self.item, self.model, iter, self.values["textView"]["column"], text_textView)
        
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.window.destroy()

    def control_unique(self, name, model, column, data, iter):
        """
        Control if data is unique.
        @return None if data are dulplicat and user do not want changed exist data. Return Iter for store date
                if data are not duplicate or data are duplicate and user can change them.
        """
        if iter:
            path = model.get_path(iter)
        else:
            path = None
            
        for row in model:
            if row[column] == data and self.model.get_path(row.iter) != path:
                md = gtk.MessageDialog(self.window, 
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_YES_NO, "%s \"%s\" already specified.\n\nRewrite stored data ?" % (name, data,))
                md.set_title("Information exist")
                result = md.run()
                md.destroy()
                if result == gtk.RESPONSE_NO:
                    return False
                else: 
                    return model.get_path(row.iter)
        return path
    
    def control_empty(self, data, name):
        """
        Control data if are not empty.
        @return True if not empty else return false
        """
        if (data == "" or data == None):
            md = gtk.MessageDialog(self.window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, " \"%s\" can't be empty." % (name))
            md.set_title("Info")
            md.run()
            md.destroy()
            return False
        return True




            
            
#class EditTitle(commands.DataHandler, abstract.EnterList):
    
    #COLUMN_MARK_ROW = 0
    #COLUMN_LAN = 1
    #COLUMN_TITLE = 2
    
    #def __init__(self, core, treeView):
        #commands.DataHandler.__init__(self, core)
        #self.core = core
        #self.treeView = treeView
        #self.iter_del=None
        #self.model = gtk.ListStore(str, str, str)
        #abstract.EnterList.__init__(self, core, "EditTitle",self.model, self.treeView)
        
        #self.add_receiver("EditTitle", "del", self.__del_row)
        #self.add_receiver("EditTitle", "edit", self.__edit_row)
        
        #cell = self.set_insertColumnText("Language", EditTitle.COLUMN_LAN, True, True)
        #cell = self.set_insertColumnText("Title", EditTitle.COLUMN_TITLE, False, False)
        
    #def __del_row(self):
        #self.model.remove(self.iter_del)
    
    #def __edit_row(self):
        #self.model[self.edit_path][self.edit_column] = self.edit_text
    
    #def fill(self,data):

        #self.selected_old = None
        #self.model.clear()
        #if data != None:
            #for key in data.keys():
                #self.model.append(["", key, data[key]])
        #iter = self.model.append(None)
        #self.model.set(iter,EditTitle.COLUMN_MARK_ROW,"*")
        
#class DHEditDescription(DataHandler, abstract.EnterList):
    
    #COLUMN_MARK_ROW = 0
    #COLUMN_LANG = 1
    #COLUMN_DES_INFO = 2
    #COLUMN_DES = 3
    
    #def __init__(self, core, treeView, sw_description):
        #DataHandler.__init__(self, core)
        #self.core = core
        #self.treeView = treeView
        #self.iter_del=None
        #self.selected_des = None
        #model = gtk.ListStore(str, str, str, str)
        #abstract.EnterList.__init__(self, core, "DHEditDescription",model, self.treeView)
        
        #self.add_receiver("DHEditDescription", "del", self.__del_row)
        
        #cell = self.set_insertColumnText("Language", DHEditDescription.COLUMN_LANG)
        #cell.connect("edited", self.__cd_editLang, DHEditDescription.COLUMN_LANG)
        #cell = self.set_insertColumnInfo("Description", DHEditDescription.COLUMN_DES_INFO, True)
                
        #self.description = HtmlTextView()
        #self.description.set_wrap_mode(gtk.WRAP_WORD)
        #self.description.set_editable(True)
        #self.description.connect("key-release-event", self.__edit_des)
        #sw_description.add(self.description)
        #sw_description.show_all()

        #self.selection.connect("changed", self.__cb_item_changed)
        
    #def __cb_item_changed(self, widget):

        #self.description.get_buffer().set_text("")
        #if self.selection != None: 
            #(model, iter) = self.selection.get_selected( )
            #if iter: 
                #self.selected_des = iter
                #text = self.model.get_value(iter, DHEditDescription.COLUMN_DES) 
                #if  text != "" and text != None:
                    #self.description.display_html(self.model.get_value(iter, DHEditDescription.COLUMN_DES))
            #else:
                #self.selected_des = None
                
    #def __edit_des(self, widget, event):
        #if self.selected_des != None:
            #buff = self.description.get_buffer()
            #iter_start = buff.get_start_iter()
            #iter_end = buff.get_end_iter()
            #des = buff.get_text(iter_start, iter_end, True)
            #self.model.set(self.selected_des, DHEditDescription.COLUMN_DES, "<body>"+des+"</body>")
            #self.model.set(self.selected_des, DHEditDescription.COLUMN_DES_INFO, des)
    
    #def __del_row(self):
        #self.model.remove(self.iter_del)
        
    #def __cd_editLang(self, cellrenderertext, path, new_text, column):
        #self.model[path][column] = new_text

    #def __cd_editDes(self, cellrenderertext, path, new_text, column):
        #self.model[path][column] = new_text
    
    #def fill(self,data):
        
        #self.selected_old = None
        #self.model.clear()
        #if data != []:
            #for key in data.keys():
                #des = data[key].replace("xhtml:","")
                #des = des.replace("xmlns:", "")
                #des_info = des[:30].replace("\n","")
                #des_info = des_info.replace("\t","")
                #des = "<body>"+des+"</body>"
                #self.model.append(["", key, des, des])
        #iter = self.model.append(None)
        #self.model.set(iter,DHEditDescription.COLUMN_MARK_ROW,"*")