from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.menus import MenuMaster, RolePermission
from models.user import User


router = APIRouter(
    prefix="/menus",
    tags=["Menus"]
)


# ============================================================
# SCHEMAS
# ============================================================

class MenuCreate(BaseModel):
    menu_name: str
    menu_code: str
    path: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 1
    is_active: bool = True


class MenuUpdate(BaseModel):
    menu_name: Optional[str] = None
    menu_code: Optional[str] = None
    path: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PermissionCreate(BaseModel):
    user_id: int
    menu_id: int
    can_view: bool = True
    can_add: bool = False
    can_edit: bool = False
    can_delete: bool = False
    is_active: bool = True


class PermissionUpdate(BaseModel):
    can_view: Optional[bool] = None
    can_add: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    is_active: Optional[bool] = None


# ============================================================
# HELPER
# ============================================================

def normalize_parent_id(parent_id: Optional[int]) -> Optional[int]:
    """
    Convert parent_id=0 to None.

    Root/top-level menus should have:
        parent_id = NULL

    Child menus should have:
        parent_id = actual menu ID
    """

    if parent_id == 0:
        return None

    return parent_id


def menu_to_dict(menu: MenuMaster):
    return {
        "id": menu.id,
        "menu_name": menu.menu_name,
        "menu_code": menu.menu_code,
        "path": menu.path,
        "icon": menu.icon,
        "parent_id": menu.parent_id,
        "sort_order": menu.sort_order,
        "is_active": menu.is_active,
        "created_at": menu.created_at,
    }


def permission_to_dict(permission: RolePermission):
    return {
        "id": permission.id,
        "user_id": permission.user_id,
        "menu_id": permission.menu_id,
        "can_view": permission.can_view,
        "can_add": permission.can_add,
        "can_edit": permission.can_edit,
        "can_delete": permission.can_delete,
        "is_active": permission.is_active,
        "created_at": permission.created_at,
    }


# ============================================================
# CREATE MENU
# ============================================================

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_menu(
    data: MenuCreate,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check duplicate menu code
    # --------------------------------------------------------

    existing_menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.menu_code == data.menu_code)
        .first()
    )

    if existing_menu:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menu code already exists"
        )

    # --------------------------------------------------------
    # Normalize parent ID
    # --------------------------------------------------------

    parent_id = normalize_parent_id(data.parent_id)

    # --------------------------------------------------------
    # Validate parent menu
    # --------------------------------------------------------

    if parent_id is not None:

        parent_menu = (
            db.query(MenuMaster)
            .filter(MenuMaster.id == parent_id)
            .first()
        )

        if not parent_menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent menu not found"
            )

    # --------------------------------------------------------
    # Create menu
    # --------------------------------------------------------

    menu = MenuMaster(
        menu_name=data.menu_name,
        menu_code=data.menu_code,
        path=data.path,
        icon=data.icon,
        parent_id=parent_id,
        sort_order=data.sort_order,
        is_active=data.is_active
    )

    db.add(menu)

    try:
        db.commit()
        db.refresh(menu)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu"
        )

    return {
        "message": "Menu created successfully",
        "data": menu_to_dict(menu)
    }


# ============================================================
# GET ALL MENUS
# ============================================================

@router.get("/")
def get_all_menus(
    db: Session = Depends(get_db)
):
    menus = (
        db.query(MenuMaster)
        .order_by(
            MenuMaster.sort_order.asc(),
            MenuMaster.id.asc()
        )
        .all()
    )

    return {
        "message": "Menus fetched successfully",
        "count": len(menus),
        "data": [
            menu_to_dict(menu)
            for menu in menus
        ]
    }


# ============================================================
# GET MENU BY ID
# ============================================================

@router.get("/{menu_id}")
def get_menu(
    menu_id: int,
    db: Session = Depends(get_db)
):
    menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.id == menu_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )

    return {
        "message": "Menu fetched successfully",
        "data": menu_to_dict(menu)
    }


# ============================================================
# UPDATE MENU
# ============================================================

@router.put("/{menu_id}")
def update_menu(
    menu_id: int,
    data: MenuUpdate,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Find menu
    # --------------------------------------------------------

    menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.id == menu_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )

    # --------------------------------------------------------
    # Check menu code
    # --------------------------------------------------------

    if data.menu_code is not None:

        duplicate_menu = (
            db.query(MenuMaster)
            .filter(
                MenuMaster.menu_code == data.menu_code,
                MenuMaster.id != menu_id
            )
            .first()
        )

        if duplicate_menu:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Menu code already exists"
            )

        menu.menu_code = data.menu_code

    # --------------------------------------------------------
    # Update fields
    # --------------------------------------------------------

    if data.menu_name is not None:
        menu.menu_name = data.menu_name

    if data.path is not None:
        menu.path = data.path

    if data.icon is not None:
        menu.icon = data.icon

    if data.sort_order is not None:
        menu.sort_order = data.sort_order

    if data.is_active is not None:
        menu.is_active = data.is_active

    # --------------------------------------------------------
    # Parent ID
    # --------------------------------------------------------

    if data.parent_id is not None:

        parent_id = normalize_parent_id(data.parent_id)

        # Cannot make itself its own parent
        if parent_id == menu_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A menu cannot be its own parent"
            )

        if parent_id is not None:

            parent_menu = (
                db.query(MenuMaster)
                .filter(MenuMaster.id == parent_id)
                .first()
            )

            if not parent_menu:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent menu not found"
                )

        menu.parent_id = parent_id

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:
        db.commit()
        db.refresh(menu)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu"
        )

    return {
        "message": "Menu updated successfully",
        "data": menu_to_dict(menu)
    }


# ============================================================
# DELETE MENU
# ============================================================

@router.delete("/{menu_id}")
def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Find menu
    # --------------------------------------------------------

    menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.id == menu_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )

    # --------------------------------------------------------
    # Check child menus
    # --------------------------------------------------------

    child_menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.parent_id == menu_id)
        .first()
    )

    if child_menu:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete menu because child menus exist"
        )

    # --------------------------------------------------------
    # Delete permissions associated with menu
    # --------------------------------------------------------

    (
        db.query(RolePermission)
        .filter(RolePermission.menu_id == menu_id)
        .delete(
            synchronize_session=False
        )
    )

    # --------------------------------------------------------
    # Delete menu
    # --------------------------------------------------------

    db.delete(menu)

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete menu"
        )

    return {
        "message": "Menu deleted successfully"
    }


# ============================================================
# CREATE USER MENU PERMISSION
# ============================================================

@router.post(
    "/permissions/create",
    status_code=status.HTTP_201_CREATED
)
def create_permission(
    data: PermissionCreate,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == data.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Check menu
    # --------------------------------------------------------

    menu = (
        db.query(MenuMaster)
        .filter(MenuMaster.id == data.menu_id)
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )

    # --------------------------------------------------------
    # Check duplicate permission
    # --------------------------------------------------------

    existing_permission = (
        db.query(RolePermission)
        .filter(
            RolePermission.user_id == data.user_id,
            RolePermission.menu_id == data.menu_id
        )
        .first()
    )

    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already exists for this user and menu"
        )

    # --------------------------------------------------------
    # Create permission
    # --------------------------------------------------------

    permission = RolePermission(
        user_id=data.user_id,
        menu_id=data.menu_id,
        can_view=data.can_view,
        can_add=data.can_add,
        can_edit=data.can_edit,
        can_delete=data.can_delete,
        is_active=data.is_active
    )

    db.add(permission)

    try:
        db.commit()
        db.refresh(permission)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create permission"
        )

    return {
        "message": "Permission created successfully",
        "data": permission_to_dict(permission)
    }


# ============================================================
# GET USER PERMISSIONS
# ============================================================

@router.get("/permissions/user/{user_id}")
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Get permissions
    # --------------------------------------------------------

    permissions = (
        db.query(RolePermission)
        .filter(
            RolePermission.user_id == user_id
        )
        .order_by(RolePermission.menu_id.asc())
        .all()
    )

    return {
        "message": "User permissions fetched successfully",
        "user_id": user_id,
        "count": len(permissions),
        "data": [
            permission_to_dict(permission)
            for permission in permissions
        ]
    }


# ============================================================
# UPDATE USER MENU PERMISSION
# ============================================================

@router.put("/permissions/{permission_id}")
def update_permission(
    permission_id: int,
    data: PermissionUpdate,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Find permission
    # --------------------------------------------------------

    permission = (
        db.query(RolePermission)
        .filter(RolePermission.id == permission_id)
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    # --------------------------------------------------------
    # Update fields
    # --------------------------------------------------------

    if data.can_view is not None:
        permission.can_view = data.can_view

    if data.can_add is not None:
        permission.can_add = data.can_add

    if data.can_edit is not None:
        permission.can_edit = data.can_edit

    if data.can_delete is not None:
        permission.can_delete = data.can_delete

    if data.is_active is not None:
        permission.is_active = data.is_active

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:
        db.commit()
        db.refresh(permission)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permission"
        )

    return {
        "message": "Permission updated successfully",
        "data": permission_to_dict(permission)
    }


# ============================================================
# DELETE USER MENU PERMISSION
# ============================================================

@router.delete("/permissions/{permission_id}")
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db)
):
    permission = (
        db.query(RolePermission)
        .filter(RolePermission.id == permission_id)
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    db.delete(permission)

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete permission"
        )

    return {
        "message": "Permission deleted successfully"
    }


# ============================================================
# GET USER SIDEBAR
# ============================================================

@router.get("/user/{user_id}/sidebar")
def get_user_sidebar(
    user_id: int,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Get active permissions with active menus
    # --------------------------------------------------------

    results = (
        db.query(
            MenuMaster,
            RolePermission
        )
        .join(
            RolePermission,
            RolePermission.menu_id == MenuMaster.id
        )
        .filter(
            RolePermission.user_id == user_id,
            RolePermission.can_view == True,
            RolePermission.is_active == True,
            MenuMaster.is_active == True
        )
        .order_by(
            MenuMaster.sort_order.asc(),
            MenuMaster.id.asc()
        )
        .all()
    )

    # --------------------------------------------------------
    # Convert menus
    # --------------------------------------------------------

    menus = []

    for menu, permission in results:

        menus.append({
            "id": menu.id,
            "menu_name": menu.menu_name,
            "menu_code": menu.menu_code,
            "path": menu.path,
            "icon": menu.icon,
            "parent_id": menu.parent_id,
            "sort_order": menu.sort_order,
            "can_view": permission.can_view,
            "can_add": permission.can_add,
            "can_edit": permission.can_edit,
            "can_delete": permission.can_delete
        })

    # --------------------------------------------------------
    # Build hierarchy
    # --------------------------------------------------------

    menu_map = {}

    for menu in menus:
        menu["children"] = []
        menu_map[menu["id"]] = menu

    sidebar = []

    for menu in menus:

        parent_id = menu["parent_id"]

        if parent_id is None:
            sidebar.append(menu)

        elif parent_id in menu_map:
            menu_map[parent_id]["children"].append(menu)

    return {
        "message": "Sidebar fetched successfully",
        "user_id": user_id,
        "data": sidebar
    }

