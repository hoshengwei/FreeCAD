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


QT_TRANSLATE_NOOP = FreeCAD.Qt.QT_TRANSLATE_NOOP
translate = FreeCAD.Qt.translate


class BIM_StoreyManager:
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
        self.stories = []  # for the stories already exist in the building
        self.modified_stories = []  # to collect the modified stories

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
        self.dialog.buttonBox.accepted.connect(self.accept)

        self.dialog.show()
        self.get_buildings()

    def update(self):
        self.stories.clear()
        self.dialog.tree.clear()
        # Load every existing storeys belongs to the building
        building = self.dialog.comboBuilding.currentData()
        stories = []
        for storey in building.OutList:
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
                stories.append((storey, sub_stories))
                sorted_stories = sorted(
                    stories, key=lambda x: get_elevation(x[0]), reverse=True
                )
                # print(sorted_stories)
                # for story in sorted_stories:
                #     print(story[0].Label)
                #     print(get_elevation(story[0]))
                self.stories = sorted_stories
        # fill the tree with QTreeWidgetItem
        self.getTreeViewItems()
        self.dialog.tree.expandAll()

    def insert_above(self):
        self.insert_storey_item("above")

    def insert_below(self):
        self.insert_storey_item("below")

    def mezzanine(self):
        self.update()

    def delete_storey(self):
        self.update()

    # def selected_building_changed(self):
    #     self.update()

    def accept(self):
        print("Accept", self.stories)

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
        from PySide import QtGui

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
            h_user_str = FreeCAD.Units.Quantity(h, FreeCAD.Units.Length).UserString

            storey_item = QtGui.QTreeWidgetItem([storey.Label, z_user_str, h_user_str])
            storey_item.setIcon(0, QtGui.QIcon(storey.ViewObject.Proxy.getIcon()))

            # deal with mezzanine_storey if have
            if mezzanine_stories:
                for mezz_storey in mezzanine_stories:
                    mezz_z = get_elevation(mezz_storey)
                    mezz_z_user_str = FreeCAD.Units.Quantity(
                        mezz_z, FreeCAD.Units.Length
                    ).UserString
                    mezz_storey_item = QtGui.QTreeWidgetItem(
                        [mezz_storey.Label, mezz_z_user_str, None]
                    )
                    mezz_storey_item.setIcon(
                        0, QtGui.QIcon(mezz_storey.ViewObject.Proxy.getIcon())
                    )
                    storey_item.addChild(mezz_storey_item)

            self.dialog.tree.addTopLevelItem(storey_item)

    def make_new_story_item(self):
        from PySide import QtGui

        # new_storey = Arch.makeFloor()
        new_storey_item = QtGui.QTreeWidgetItem(
            [
                "New Level",
                FreeCAD.Units.Quantity(0, FreeCAD.Units.Length).UserString,
                FreeCAD.Units.Quantity(0, FreeCAD.Units.Length).UserString,
            ]
        )
        new_storey_item.setIcon(0, QtGui.QIcon(":/icons/Arch_Floor_Tree.svg"))
        return new_storey_item

    def insert_storey_item(self, position):
        """Insert storey can choose insert above or below"""

        selected_storey_item = self.dialog.tree.currentItem()
        new_storey_item = self.make_new_story_item()

        if selected_storey_item:
            index = self.dialog.tree.indexOfTopLevelItem(selected_storey_item)
            if index != -1:
                if position == "above":
                    self.dialog.tree.insertTopLevelItem(index, new_storey_item)
                elif position == "below":
                    self.dialog.tree.insertTopLevelItem(index + 1, new_storey_item)
            else:
                # mezzanine_storey
                parent_storey_item = selected_storey_item.parent()
                if parent_storey_item:
                    index = parent_storey_item.indexOfChild(selected_storey_item)
                    if position == "above":
                        parent_storey_item.insertChild(index, new_storey_item)
                    elif position == "below":
                        parent_storey_item.insertChild(index + 1, new_storey_item)
        else:  # if not select any storey
            if position == "above":
                self.dialog.tree.insertTopLevelItem(0, new_storey_item)
            elif position == "below":
                self.dialog.tree.addTopLevelItem(new_storey_item)

        self.modified_stories.append(new_storey_item)


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
