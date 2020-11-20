from dcodex.models import * 
from dcodex_lectionary.models import * 

def get_movable_day(day):
    new_day, _ = MovableDay.objects.update_or_create( 
        day_of_week=day.day_of_week,
        season=day.period,
        week=day.week,
        weekday_number=day.weekday_number,
        defaults=dict(
            earliest_date=day.earliest_date,
            latest_date=day.latest_date,
        )
    )
    return new_day

def get_other_day( day ):
    if day.date:
        new_day, _ = FixedDay.objects.update_or_create(
            date=day.date,
        )
    elif 'Resurrection' in day.description:
        rank = int(day.description.split()[-1])
        new_day, _ = EothinaDay.objects.update_or_create(rank=rank)
    else:
        new_day, _ = MiscDay.objects.update_or_create(description=day.description)

    return new_day



def run():
    for day in DayOfYear.objects.all():
        get_movable_day( day )

    for day in FixedDate.objects.all():
        get_other_day( day )


    for membership in LectionInSystem.objects.all():
        if membership.day_of_year:
            membership.day = get_movable_day(membership.day_of_year)
        elif membership.fixed_date:
            membership.day = get_other_day(membership.fixed_date)
        membership.save()
