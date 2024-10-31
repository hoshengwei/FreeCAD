# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""This module contains FreeCAD commands for the BIM workbench"""

import FreeCAD
import FreeCADGui
from PySide.QtWidgets import QDialog


QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate

# MODIFIED_COLOR = "lightgoldenrodyellow"
MODIFIED_COLOR = "lightyellow"
UPDATEINTERVAL = 50
DEFAULT_HEIGHT = 3000  # default storey height = 3m


class BIM_StoreyManager:
    def __init__(self, lv=None, h=None):
        self.default_lv = lv
        self.default_h = h

    def GetResources(self):
        return {
            "Pixmap": "BIM_Levels",
            "MenuText": QT_TRANSLATE_NOOP("BIM_StoreyManager", "Manage storey ..."),
            "ToolTip": QT_TRANSLATE_NOOP(
                "BIM_StoreyManager",
                "Manage the storey height and elevation in your building object",
            ),
        }

    def IsActive(self):
        v = hasattr(FreeCADGui.getMainWindow().getActiveWindow(), "getSceneGraph")
        return v

    def Activated(self):
        # from PySide.QtWidgets import QTreeWidget, QAbstractItemView

        self.stories = []  # for the stories already exist in the building
        self.temp_stories = []  # tree view stories holder
        self.new_item_counter = 1

        # load the dialog and set the tree model up
        self.dialog = FreeCADGui.PySideUic.loadUi(":/ui/dialogStoreyManager.ui")

        # center the dialog over FreeCAD window
        mw = FreeCADGui.getMainWindow()
        self.dialog.move(
            mw.frameGeometry().topLeft()
            + mw.rect().center()
            - self.dialog.rect().center()
        )

        # connect signals
        self.dialog.buttonInsertAbove.clicked.connect(self.insert_above)
        self.dialog.buttonInsertBelow.clicked.connect(self.insert_below)
        self.dialog.buttonMezzanine.clicked.connect(self.mezzanine)
        self.dialog.buttonDelete.clicked.connect(self.delete_storey)
        self.dialog.comboBuilding.currentIndexChanged.connect(self.update)
        self.dialog.buttonBox.accepted.connect(self.apply_changes)
        self.dialog.tree.itemChanged.connect(self.item_changed)

        self.get_buildings()
        self.dialog.show()

    def update(self):
        self.stories.clear()
        self.temp_stories.clear()
        self.dialog.tree.clear()
        # Load every existing storeys belongs to the building
        self.building = self.dialog.comboBuilding.currentData()
        stories = []
        for storey in self.building.OutList:
            if (
                getattr(storey, "IfcType", None) == "Building Storey"
                or getattr(storey, "IfcClass", None) == "IfcBuildingStorey"
            ):
                # for mezzanine floor
                sub_stories = []
                for mezzanine_storey in storey.OutList:
                    if (
                        getattr(mezzanine_storey, "IfcType", None) == "Building Storey"
                        or getattr(mezzanine_storey, "IfcClass", None)
                        == "IfcBuildingStorey"
                    ):
                        sub_stories.append(mezzanine_storey)
                # storey data format
                stories.append((storey, sub_stories))
                sorted_stories = sorted(
                    stories, key=lambda x: get_elevation(x[0]), reverse=True
                )
                self.stories = sorted_stories
        # fill the tree with QTreeWidgetItem
        self.getTreeViewItems()
        self.dialog.tree.expandAll()

    def insert_above(self):
        self.insert_storey_item("above")

    def insert_below(self):
        self.insert_storey_item("below")

    def delete_storey(self):
        # TODO: 需要先確認該樓層是否底下還有其他物件才允許刪除
        for story in self.temp_stories:
            print("------")
            print(story[0].text(0))
            print(story[1])
            print(story[2])
            if story[2]:
                for s in story[2]:
                    print("@@@")
                    print(s[0].text(0))
                    print(s[1])

    def mezzanine(self):
        selected_storey_items = self.dialog.tree.selectedItems()
        selected_storey_item = (
            selected_storey_items[0] if selected_storey_items else None
        )
        index = self.dialog.tree.indexOfTopLevelItem(selected_storey_item)

        if selected_storey_item is None:
            return

        if index == -1:  # if choose mezz floor
            # TODO: need to add pop warning dialog?
            return

        selected_storey_item_elevation = FreeCAD.Units.parseQuantity(
            selected_storey_item.text(1)
        ).Value
        new_storey_item = self.make_new_story_item(z=selected_storey_item_elevation)
        self.highlight_item(new_storey_item)
        storey_to_insert = (new_storey_item, None)
        selected_storey_item.addChild(new_storey_item)
        selected_storey_item.setExpanded(True)
        self.temp_stories[index][2].append(storey_to_insert)

    def get_buildings(self):
        """fill the building combobox"""
        from PySide import QtGui

        # for collecting all the building in the document
        self.buildings = []
        for obj in FreeCAD.ActiveDocument.Objects:
            if (
                getattr(obj, "IfcType", None) == "Building"
                or getattr(obj, "IfcClass", None) == "IfcBuilding"
            ):
                self.buildings.append(obj)
                # add icon
                icon = QtGui.QIcon(obj.ViewObject.Proxy.getIcon())
                self.dialog.comboBuilding.addItem(icon, obj.Label, obj)

        index = 0
        # if select building obj before using the storey manager, will use that building priority
        if FreeCADGui.Selection.getSelection():
            pre_select_building = FreeCADGui.Selection.getSelection()[0]
            # TODO: if not select building object, make it find the building it belong to
            index = (
                self.buildings.index(pre_select_building)
                if pre_select_building in self.buildings
                else 0
            )
            self.dialog.comboBuilding.setCurrentIndex(index)

    def getTreeViewItems(self):
        from PySide import QtGui, QtCore

        for i in range(len(self.stories)):
            storey = self.stories[i][0]
            up_storey = storey if i == 0 else self.stories[i - 1][0]
            mezzanine_stories = (
                self.stories[i][1] if self.stories[i][1] is not None else None
            )

            # z: elevation
            z = get_elevation(storey)
            z_user_str = FreeCAD.Units.Quantity(z, FreeCAD.Units.Length).UserString

            # h: storey height
            h = get_elevation(up_storey) - z
            if h == 0:
                h = storey.Height if hasattr(storey, "Height") else DEFAULT_HEIGHT
            h_user_str = FreeCAD.Units.Quantity(h, FreeCAD.Units.Length).UserString

            storey_item = QtGui.QTreeWidgetItem([storey.Label, z_user_str, h_user_str])
            storey_item.setIcon(0, QtGui.QIcon(storey.ViewObject.Proxy.getIcon()))
            storey_item.setFlags(storey_item.flags() | QtCore.Qt.ItemIsEditable)
            self.temp_stories.append((storey_item, storey, []))

            # deal with mezzanine_storey if have
            if mezzanine_stories:
                for mezz_storey in mezzanine_stories:
                    mezz_z = get_elevation(mezz_storey)
                    mezz_z_user_str = FreeCAD.Units.Quantity(
                        mezz_z, FreeCAD.Units.Length
                    ).UserString
                    mezz_h = mezz_storey.Height if hasattr(mezz_storey, "Height") else 0
                    mezz_h_user_str = FreeCAD.Units.Quantity(
                        mezz_h, FreeCAD.Units.Length
                    ).UserString
                    mezz_storey_item = QtGui.QTreeWidgetItem(
                        [mezz_storey.Label, mezz_z_user_str, mezz_h_user_str]
                    )
                    mezz_storey_item.setIcon(
                        0, QtGui.QIcon(mezz_storey.ViewObject.Proxy.getIcon())
                    )
                    mezz_storey_item.setFlags(
                        mezz_storey_item.flags() | QtCore.Qt.ItemIsEditable
                    )
                    storey_item.addChild(mezz_storey_item)
                    self.temp_stories[-1][2].append((mezz_storey_item, mezz_storey))

            self.dialog.tree.addTopLevelItem(storey_item)

    def make_new_story_item(self, z=0, h=0):
        from PySide import QtGui, QtCore

        # not make instance until click apply button, here should only update tree view
        new_storey_item = QtGui.QTreeWidgetItem(
            [
                f"New Level_{self.new_item_counter}",
                FreeCAD.Units.Quantity(z, FreeCAD.Units.Length).UserString,
                FreeCAD.Units.Quantity(h, FreeCAD.Units.Length).UserString,
            ]
        )
        new_storey_item.setIcon(0, QtGui.QIcon(":/icons/Arch_Floor_Tree.svg"))
        new_storey_item.setFlags(new_storey_item.flags() | QtCore.Qt.ItemIsEditable)
        self.new_item_counter += 1
        return new_storey_item

    def insert_storey_item(self, position):
        """Insert storey can choose insert above or below"""
        from PySide import QtCore

        selected_storey_item = self.dialog.tree.currentItem()
        selected_storey_item_height = FreeCAD.Units.parseQuantity(
            selected_storey_item.text(2)
        ).Value

        selected_storey_item_elevation = FreeCAD.Units.parseQuantity(
            selected_storey_item.text(1)
        ).Value
        new_storey_item = self.make_new_story_item(
            z=selected_storey_item_elevation, h=selected_storey_item_height
        )
        self.highlight_item(new_storey_item)
        storey_to_insert = (new_storey_item, None, [])

        if selected_storey_item:
            index = self.dialog.tree.indexOfTopLevelItem(selected_storey_item)
            if index != -1:
                if position == "above":
                    self.dialog.tree.insertTopLevelItem(index, new_storey_item)
                    self.temp_stories.insert(index, storey_to_insert)
                    QtCore.QTimer.singleShot(
                        UPDATEINTERVAL,
                        lambda: self._updateAboveFloorLevel(selected_storey_item),
                    )
                elif position == "below":
                    self.dialog.tree.insertTopLevelItem(index + 1, new_storey_item)
                    self.temp_stories.insert(index + 1, storey_to_insert)
                    QtCore.QTimer.singleShot(
                        UPDATEINTERVAL,
                        lambda: self._updateBelowFloorLevel(selected_storey_item),
                    )
            else:
                # mezzanine_storey
                parent_storey_item = selected_storey_item.parent()
                p_index = self.dialog.tree.indexOfTopLevelItem(parent_storey_item)
                print(p_index)
                if parent_storey_item:
                    index = parent_storey_item.indexOfChild(selected_storey_item)
                    if position == "above":
                        parent_storey_item.insertChild(index, new_storey_item)
                        self.temp_stories[p_index][2].insert(
                            index, storey_to_insert[:2]
                        )
                    elif position == "below":
                        parent_storey_item.insertChild(index + 1, new_storey_item)
                        self.temp_stories[p_index][2].insert(
                            index + 1, storey_to_insert[:2]
                        )
        else:  # if not select any storey
            if position == "above":
                self.dialog.tree.insertTopLevelItem(0, new_storey_item)
                self.temp_stories.insert(0, storey_to_insert)
            elif position == "below":
                self.dialog.tree.addTopLevelItem(new_storey_item)
                self.temp_stories.append(storey_to_insert)

    def highlight_item(self, item, column=None, bg_color=MODIFIED_COLOR):
        """column could be None, col_index, [col_index, col_index,...]"""
        from PySide import QtGui

        if column or column == 0:
            column = [column] if not isinstance(column, (list, tuple)) else column
            for i in column:
                item.setBackground(i, QtGui.QBrush(QtGui.QColor(bg_color)))
        else:  # changed entire item color
            column_count = self.dialog.tree.columnCount()
            for column in range(column_count):
                item.setBackground(column, QtGui.QBrush(QtGui.QColor(bg_color)))

    def item_changed(self, item, column):
        print("changed")
        self.highlight_item(item, column)
        if column == 1:
            self._updateAboveFloorLevel(item)
            self._updateBelowFloorLevel(item)
        if column == 2:
            self._updateAboveFloorLevel(item)

    def apply_changes(self):
        import Arch

        for temp_storey_item, temp_storey, temp_mezz_stories in self.temp_stories:
            # if not exist -> create new storey
            if temp_storey is None:
                new_storey = Arch.makeFloor()
                new_storey.Label = temp_storey_item.text(0)
                new_storey.Placement.Base.z = FreeCAD.Units.parseQuantity(
                    temp_storey_item.text(1)
                )
                new_storey.Elevation = new_storey.Placement.Base.z
                self.building.addObject(new_storey)

                # # 更新子 story
                # for child_item, sub_story in sub_items:
                #     sub_story['name'] = child_item.text(0)
                #     sub_story['elevation'] = float(child_item.text(1))
                #     sub_story['height'] = float(child_item.text(2))

    def _updateAboveFloorLevel(self, item):
        """update every floors level which above the edited floor"""
        current_index = self.dialog.tree.indexOfTopLevelItem(item)
        if current_index == -1:
            return
        new_elevation = (
            FreeCAD.Units.parseQuantity(item.text(1)).Value
            + FreeCAD.Units.parseQuantity(item.text(2)).Value
        )
        for i in range(current_index - 1, -1, -1):
            current_item = self.dialog.tree.topLevelItem(i)
            print(current_item.text(0))
            current_item.setText(
                1,
                FreeCAD.Units.Quantity(new_elevation, FreeCAD.Units.Length).UserString,
            )
            new_elevation += FreeCAD.Units.parseQuantity(current_item.text(2)).Value

    def _updateBelowFloorLevel(self, item):
        """update every floors level which below the edited floor"""
        current_index = self.dialog.tree.indexOfTopLevelItem(item)
        print("current_index", current_index)
        if current_index == -1:
            return
        for i in range(current_index + 1, self.dialog.tree.topLevelItemCount()):
            print(i)
            previous_item_elevation = FreeCAD.Units.parseQuantity(
                self.dialog.tree.topLevelItem(i - 1).text(1)
            ).Value
            print("pv", previous_item_elevation)
            current_item = self.dialog.tree.topLevelItem(i)
            current_item_height = FreeCAD.Units.parseQuantity(
                current_item.text(2)
            ).Value
            print("ch", current_item_height)
            new_elevation = previous_item_elevation - current_item_height
            current_item.setText(
                1,
                FreeCAD.Units.Quantity(new_elevation, FreeCAD.Units.Length).UserString,
            )


def get_elevation(obj):
    """return z: float"""
    # z: elevation
    z = obj.Placement.Base.z
    if z == 0:
        # override with Elevation property if available
        if hasattr(obj, "Elevation"):
            z = obj.Elevation.Value
    return z


FreeCADGui.addCommand("BIM_StoreyManager", BIM_StoreyManager())
