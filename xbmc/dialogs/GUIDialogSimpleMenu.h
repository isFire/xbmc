/*
 *  Copyright (C) 2005-2013 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#pragma once

#include "FileItem.h"
#include "filesystem/Directory.h"
#include <string>

class CGUIDialogSimpleMenu
{
public:

  /*! \brief Show dialog allowing selection of wanted playback item */
  static bool ShowPlaySelection(CFileItem& item);
  static bool ShowPlaySelection(CFileItem& item, const std::string& directory);

protected:
  static bool GetDirectoryItems(const std::string &path, CFileItemList &items, const XFILE::CDirectory::CHints &hints);
};
