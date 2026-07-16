from flask import Flask, render_template, request, redirect, url_for, session

from excel import (
    load_consumers,
    find_generators,
    load_generators,
    get_accessory
)


app = Flask(__name__)

app.secret_key = "generator_demo_key"


# ==========================
# СТАРТ
# ==========================

@app.route("/")
def start():

    session.clear()

    return render_template(
        "start.html"
    )


# ==========================
# НАПРЯЖЕНИЕ
# ==========================

@app.route("/voltage", methods=["POST"])
def voltage():

    session["voltage"] = request.form["voltage"]

    session["selected_consumers"] = []

    session["power"] = 0

    session["cart"] = []

    return redirect(
        url_for("consumers")
    )


# ==========================
# ПОТРЕБИТЕЛИ
# ==========================

@app.route("/consumers")
def consumers():

    df = load_consumers()

    categories = (
        df["Категория"]
        .dropna()
        .unique()
        .tolist()
    )


    return render_template(
        "consumers.html",
        categories=categories,
        consumers=[],
        selected=session.get(
            "selected_consumers",
            []
        ),
        power=session.get(
            "power",
            0
        )
    )


@app.route("/category", methods=["POST"])
def category():

    category_name = request.form["category"]

    df = load_consumers()


    consumers = df[
        df["Категория"] == category_name
    ].to_dict("records")


    return render_template(
        "consumers.html",

        categories=df["Категория"]
        .dropna()
        .unique()
        .tolist(),

        consumers=consumers,

        selected=session.get(
            "selected_consumers",
            []
        ),

        power=session.get(
            "power",
            0
        )
    )


@app.route("/add_consumer", methods=["POST"])
def add_consumer():

    consumer_id = int(
        request.form["id"]
    )


    df = load_consumers()


    row = df[
        df["id"] == consumer_id
    ]


    if not row.empty:

        item = row.iloc[0]


        selected = session.get(
            "selected_consumers",
            []
        )


        if not any(
            x["id"] == consumer_id
            for x in selected
        ):

            selected.append(
                {
                    "id": consumer_id,
                    "name": item["Прибор"],
                    "work": int(item["Мощность, Вт"]),
                    "start": int(item["Пусковые токи, Вт"])
                }
            )


        session["selected_consumers"] = selected


    recalculate_power()


    return redirect(
        url_for("consumers")
    )


def recalculate_power():

    selected = session.get(
        "selected_consumers",
        []
    )


    power = 0


    for item in selected:

        power += item["start"]


    session["power"] = int(
        power * 1.3
    )# ==========================
# СВОЙ ПРИБОР
# ==========================

@app.route("/custom")
def custom():

    return render_template(
        "custom.html"
    )


@app.route("/add_custom", methods=["POST"])
def add_custom():

    name = request.form["name"]

    power = int(
        request.form["power"]
    )


    selected = session.get(
        "selected_consumers",
        []
    )


    selected.append(
        {
            "id": -len(selected)-1,
            "name": name,
            "work": power,
            "start": power
        }
    )


    session["selected_consumers"] = selected


    recalculate_power()


    return redirect(
        url_for("consumers")
    )



# ==========================
# СТАРТЕР
# ==========================

@app.route("/starter")
def starter():

    return render_template(
        "starter.html"
    )


@app.route("/starter_select", methods=["POST"])
def starter_select():

    starter = request.form["starter"]

    session["starter"] = starter


    if starter == "Электрический":

        return redirect(
            url_for("avr")
        )

    else:

        session["avr"] = "Нет"

        return redirect(
            url_for("find_generators_page")
        )



# ==========================
# АВР
# ==========================

@app.route("/avr")
def avr():

    return render_template(
        "avr.html"
    )


@app.route("/avr_select", methods=["POST"])
def avr_select():

    session["avr"] = request.form["avr"]


    return redirect(
        url_for("find_generators_page")
    )



# ==========================
# ПОИСК ГЕНЕРАТОРОВ
# ==========================

@app.route("/find_generators")
def find_generators_page():


    generators = find_generators(

        voltage=session.get(
            "voltage"
        ),

        power=session.get(
            "power"
        ),

        starter=session.get(
            "starter"
        ),

        avr=session.get(
            "avr"
        )

    )


    return render_template(

        "generators.html",

        generators=generators.to_dict(
            "records"
        )

    )



# ==========================
# ВЫБОР ГЕНЕРАТОРА
# ==========================

@app.route("/generator/<int:id>")
def generator(id):


    df = load_generators()


    row = df[
        df["id"] == id
    ]


    if row.empty:

        return "Нет такого генератора"


    item = row.iloc[0]


    session["cart"] = [

        {
            "name": item["Модель"],
            "price": int(item["цена"])
        }

    ]


    return redirect(
        url_for("accessories")
    )



# ==========================
# СОПУТКА
# ==========================

@app.route("/accessories")
def accessories():

    items = []


    if session.get("starter") == "Электрический":

        avr = get_accessory(
            "АВР"
        )

        if avr is not None:

            items.append(avr)



    for name in [

        "Масло Huter 10W40",

        "Комплект колёса+ручка",

        "Удлинитель 25м 16А"

    ]:


        item = get_accessory(name)


        if item is not None:

            items.append(item)



    return render_template(

        "accessories.html",

        items=items,

        cart=session.get(
            "cart",
            []
        )

    )



@app.route("/add_accessory", methods=["POST"])
def add_accessory():

    name = request.form["name"]


    item = get_accessory(name)


    if item is not None:


        cart = session.get(
            "cart",
            []
        )


        if not any(
            x["name"] == item["Модель"]
            for x in cart
        ):


            cart.append(

                {
                    "name": item["Модель"],
                    "price": int(item["цена"])
                }

            )


        session["cart"] = cart



    return redirect(
        url_for("accessories")
    )# ==========================
# ЗАКАЗ
# ==========================

@app.route("/order")
def order():

    cart = session.get(
        "cart",
        []
    )


    total = sum(
        item["price"]
        for item in cart
    )


    return render_template(

        "order.html",

        cart=cart,

        total=total

    )



@app.route("/finish", methods=["POST"])
def finish():

    return render_template(
        "finish.html"
    )


if __name__ == "__main__":
    app.run(debug=True)