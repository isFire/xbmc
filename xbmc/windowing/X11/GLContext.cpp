/*
 *  Copyright (C) 2005-2014 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#include "GLContext.h"

bool CGLContext::IsExtSupported(const char* extension) const
{
  std::string name;

  name  = " ";
  name += extension;
  name += " ";

  return m_extensions.find(name) != std::string::npos;
}
