/*
 *  Copyright (C) 2005-2013 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#pragma once

#include "DirectoryNode.h"

namespace XFILE
{
  namespace MUSICDATABASEDIRECTORY
  {
    class CDirectoryNodeAlbumRecentlyPlayedSong : public CDirectoryNode
    {
    public:
      CDirectoryNodeAlbumRecentlyPlayedSong(const std::string& strName, CDirectoryNode* pParent);
    protected:
      bool GetContent(CFileItemList& items) const override;
    };
  }
}


