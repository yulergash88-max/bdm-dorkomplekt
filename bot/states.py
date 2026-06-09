from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    entering_phone = State()
    choosing_role = State()
    entering_company_name = State()


class NewDelivery(StatesGroup):
    entering_product_name = State()
    entering_supplier_kub = State()


class WeighDelivery(StatesGroup):
    entering_tonnage = State()


class AdminSetCoefficient(StatesGroup):
    entering_value = State()


class AdminAddUser(StatesGroup):
    choosing_role = State()
    entering_company_name = State()
    entering_phone = State()


class AdminEditUser(StatesGroup):
    entering_new_value = State()


class AdminSetProductCoefficient(StatesGroup):
    choosing_product = State()
    entering_value = State()
