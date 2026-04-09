package com.shvarsman.permissionsdemo

import android.Manifest
import android.app.Application
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

class PermissionsViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("perm_prefs", 0)

    private val _permissions = MutableStateFlow(buildInitialList())
    val permissions: StateFlow<List<PermissionItem>> = _permissions

    private fun buildInitialList(): List<PermissionItem> {
        val definitions = listOf(
            Triple(Manifest.permission.CAMERA,
                R.string.perm_camera_label,   R.string.perm_camera_desc),
            Triple(Manifest.permission.READ_CONTACTS,
                R.string.perm_contacts_label, R.string.perm_contacts_desc),
            Triple(Manifest.permission.ACCESS_FINE_LOCATION,
                R.string.perm_location_label, R.string.perm_location_desc),
        )
        return definitions.map { (perm, labelRes, descRes) ->
            PermissionItem(
                permission      = perm,
                labelRes        = labelRes,
                descriptionRes  = descRes,
                status          = resolveStatus(perm)
            )
        }
    }

    fun resolveStatus(permission: String): PermissionStatus {
        val ctx = getApplication<Application>()
        val granted = ContextCompat.checkSelfPermission(ctx, permission) ==
                PackageManager.PERMISSION_GRANTED
        if (granted) return PermissionStatus.GRANTED
        val asked = prefs.getBoolean("asked_$permission", false)
        return if (asked) PermissionStatus.DENIED else PermissionStatus.UNKNOWN
    }

    fun onPermissionResult(permission: String, granted: Boolean) {
        prefs.edit().putBoolean("asked_$permission", true).apply()
        _permissions.update { list ->
            list.map { item ->
                if (item.permission == permission)
                    item.copy(status = if (granted) PermissionStatus.GRANTED else PermissionStatus.DENIED)
                else item
            }
        }
    }

    fun onMultipleResults(results: Map<String, Boolean>) {
        results.forEach { (perm, _) ->
            prefs.edit().putBoolean("asked_$perm", true).apply()
        }
        _permissions.update { list ->
            list.map { item ->
                val granted = results[item.permission]
                if (granted != null)
                    item.copy(status = if (granted) PermissionStatus.GRANTED else PermissionStatus.DENIED)
                else item
            }
        }
    }

    fun refreshAll() {
        _permissions.update { list ->
            list.map { item -> item.copy(status = resolveStatus(item.permission)) }
        }
    }
}