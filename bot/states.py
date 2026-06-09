from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    entering_phone = State()
    choosing_role = State()
    entering_company_name = State()



class BuyerWeighDelivery(StatesGroup):
    using_numpad = State()
    confirming_tonnage = State()


class AdminSetCoefficient(StatesGroup):
    entering_value = State()


class AdminAddUser(StatesGroup):
    choosing_role = State()
    entering_company_name = State()
    choosing_weighing = State()
    entering_phone = State()


class AdminEditUser(StatesGroup):
    entering_new_value = State()


class AdminSetProductCoefficient(StatesGroup):
    choosing_product = State()
    entering_value = State()


class DateRangeReport(StatesGroup):
    entering_start_date = State()
    entering_end_date = State()
