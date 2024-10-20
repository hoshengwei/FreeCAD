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
        # load the dialog and set the tree model up
        self.dialog = FreeCADGui.PySideUic.loadUi(":/ui/dialogStoreyManager.ui")
        # self.dialog.setWindowIcon(QtGui.QIcon(":/icons/BIM_IfcElements.svg"))
        # self.dialog.ifcFileObj.addItem(ifc_commands.get_project().Label)

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

        self.dialog.show()
        self.update()

    def update(self):
        pass

    def insert_above(self):
        self.update()

    def insert_below(self):
        self.update()

    def mezzanine(self):
        self.update()

    def delete_storey(self):
        self.update()

    # def reject(self):
    #     # self.dialog.hide()
    #     return True

    def accept(self):
        pass


FreeCADGui.addCommand("BIM_StoreyManager", BIM_StoreyManager())
