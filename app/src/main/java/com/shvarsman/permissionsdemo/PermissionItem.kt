package com.shvarsman.permissionsdemo

import androidx.annotation.StringRes

data class PermissionItem(
    val permission: String,
    @StringRes val labelRes: Int,
    @StringRes val descriptionRes: Int,
    val status: PermissionStatus
)