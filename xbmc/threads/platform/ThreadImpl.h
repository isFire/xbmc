/*
 *  Copyright (C) 2005-2013 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */

#pragma once

#if (defined TARGET_POSIX)
#include "threads/platform/pthreads/ThreadImpl.h"
#elif (defined TARGET_WINDOWS)
#include "threads/platform/win/ThreadImpl.h"
#endif
