//Need to create a dummy console object so that console.log doesn't cause errors in IE
if (!window.console) {
    window.console = {};
}
if (!window.console.log) {
    window.console.log = function () {};
}

function round3dp(num) {
    return Math.round(1000 * num) / 1000;
}

function constantIrregularTimeSeries(d) {
    if (d.Type === "daily") {
        var dayStart = new Date(d.Start);
        var dayEnd = new Date(d.Start.getFullYear(), d.Start.getMonth(), d.Start.getDate(),
                              d.End.getHours(), d.End.getMinutes(), d.End.getSeconds());
        if (dayEnd < dayStart) {
            dayEnd.setDate(dayEnd.getDate() + 1);
        }
        var ts = [];
        while (dayStart < d.End) {
            ts.push(
                { date: new Date(dayStart), price: d.Value },
                { date: new Date(dayEnd), price: 0 }
            );
            
            if (ts[ts.length-1].date <= ts[ts.length-2].date ||
                    ts.length >= 3 && ts[ts.length-2].date <= ts[ts.length-3].date) {
                console.log("This should never happen. Dates should be strictly increasing");
                debugger;
            }
            
            dayStart.setDate(dayStart.getDate() + 1);
            dayEnd.setDate(dayEnd.getDate() + 1);
        }
        return ts;
    } else {
        if (d.End.getTime() <= d.Start.getTime()) {
            console.log("This should never happen. Dates should be strictly increasing");
            debugger;
        }
        return [
            { date: d.Start, price: d.Value },
            { date: d.End, price: 0 }
        ];
    }
}

function addIrregularTimeSeries(ts1, ts2) {
    var ts3 = [];
    var prevTs1 = 0;
    var prevTs2 = 0;
    var currPrice = 0;
    var n1 = ts1.length;
    var n2 = ts2.length;
    var i1 = 0, i2 = 0;
    while (i1 < n1 || i2 < n2) {
        if (i1 === n1) {
            ts3.push(ts2[i2++]);
        } else if (i2 === n2) {
            ts3.push(ts1[i1++]);
        } else if (ts1[i1].date == null || ts2[i2].date == null) {
            debugger;
        } else if (ts1[i1].date < ts2[i2].date) {
            var newTs1 = ts1[i1++];
            currPrice = round3dp(currPrice + (newTs1.price - prevTs1));
            ts3.push({ date: newTs1.date, price: currPrice });
            prevTs1 = newTs1.price;
        } else if (ts2[i2].date < ts1[i1].date) {
            var newTs2 = ts2[i2++];
            currPrice = round3dp(currPrice + (newTs2.price - prevTs2));
            ts3.push({ date: newTs2.date, price: currPrice });
            prevTs2 = newTs2.price;
        } else if (ts1[i1].date.getTime() === ts2[i2].date.getTime()) {
            // dates equal
            var newTs1 = ts1[i1++];
            var newTs2 = ts2[i2++];
            var priceIncrease = round3dp((newTs1.price - prevTs1) + (newTs2.price - prevTs2));
            if (priceIncrease !== 0) {
                currPrice = round3dp(currPrice + priceIncrease);
                if (currPrice < 0) {
                    console.log("Negative price shouldn't be possible");
                    debugger;
                }
                ts3.push({ date: newTs1.date, price: currPrice });
            }
            prevTs1 = newTs1.price;
            prevTs2 = newTs2.price;
        } else {
            console.log("This should never happen");
            debugger;
        }
        if (ts3.length >= 2 && ts3[ts3.length-1].date <= ts3[ts3.length-2].date) {
            console.log("This should never happen. Dates should be strictly increasing");
            debugger;
        }
    }
    return ts3;
}

function subtractIrregularTimeSeries(ts1, ts2) {
    var ts3 = [];
    var prevTs1 = 0;
    var prevTs2 = 0;
    var currPrice = 0;
    var n1 = ts1.length;
    var n2 = ts2.length;
    var i1 = 0, i2 = 0;
    while (i1 < n1 || i2 < n2) {
        if (i1 === n1) {
            ts3.push(ts2[i2++]);
        } else if (i2 === n2) {
            ts3.push(ts1[i1++]);
        } else if (ts1[i1].date == null || ts2[i2].date == null) {
            debugger;
        } else if (ts1[i1].date < ts2[i2].date) {
            var newTs1 = ts1[i1++];
            currPrice = round3dp(currPrice + (newTs1.price - prevTs1));
            ts3.push({ date: newTs1.date, price: currPrice });
            prevTs1 = newTs1.price;
        } else if (ts2[i2].date < ts1[i1].date) {
            var newTs2 = ts2[i2++];
            currPrice = round3dp(currPrice - (newTs2.price - prevTs2));
            ts3.push({ date: newTs2.date, price: currPrice });
            prevTs2 = newTs2.price;
        } else if (ts1[i1].date.getTime() === ts2[i2].date.getTime()) {
            // dates equal
            var newTs1 = ts1[i1++];
            var newTs2 = ts2[i2++];
            var priceIncrease = round3dp((newTs1.price - prevTs1) - (newTs2.price - prevTs2));
            if (priceIncrease !== 0) {
                currPrice = round3dp(currPrice + priceIncrease);
                if (currPrice < 0) {
                    console.log("Negative price shouldn't be possible");
                    debugger;
                }
                ts3.push({ date: newTs1.date, price: currPrice });
            }
            prevTs1 = newTs1.price;
            prevTs2 = newTs2.price;
        } else {
            console.log("This should never happen");
            debugger;
        }
        if (ts3.length >= 2 && ts3[ts3.length-1].date <= ts3[ts3.length-2].date) {
            console.log("This should never happen. Dates should be strictly increasing");
            debugger;
        }
    }
    return ts3;
}

function addIrregularTimeSeriesWithBase(ts1, ts2) {
    var ts3 = [];
    var prevTs1 = 0;
    var prevTs2 = 0;
    var currPrice = 0;
    var n1 = ts1.length;
    var n2 = ts2.length;
    var i1 = 0, i2 = 0;
    while (i1 < n1 || i2 < n2) {
        if (i1 === n1) {
            var newTs2 = ts2[i2++];
            ts3.push({ date: newTs2.date, price: newTs2.price, price0: 0 });
        } else if (i2 === n2) {
            var newTs1 = ts1[i1++];
            ts3.push({ date: newTs1.date, price: newTs1.price, price0: newTs1.price });
        } else if (ts1[i1].date == null || ts2[i2].date == null) {
            debugger;
        } else if (ts1[i1].date < ts2[i2].date) {
            var newTs1 = ts1[i1++];
            currPrice = round3dp(currPrice + (newTs1.price - prevTs1));
            ts3.push({ date: newTs1.date, price: currPrice, price0: newTs1.price });
            prevTs1 = newTs1.price;
        } else if (ts2[i2].date < ts1[i1].date) {
            var newTs2 = ts2[i2++];
            currPrice = round3dp(currPrice + (newTs2.price - prevTs2));
            ts3.push({ date: newTs2.date, price: currPrice, price0: prevTs1 });
            prevTs2 = newTs2.price;
        } else if (ts1[i1].date.getTime() === ts2[i2].date.getTime()) {
            // dates equal
            var newTs1 = ts1[i1++];
            var newTs2 = ts2[i2++];
            var priceIncrease = round3dp((newTs1.price - prevTs1) + (newTs2.price - prevTs2));
            currPrice = round3dp(currPrice + priceIncrease);
            if (currPrice < 0) {
                console.log("Negative price shouldn't be possible");
                debugger;
            }
            ts3.push({ date: newTs1.date, price: currPrice, price0: newTs1.price });
            prevTs1 = newTs1.price;
            prevTs2 = newTs2.price;
        } else {
            console.log("This should never happen");
            debugger;
        }
        if (ts3.length >= 2 && ts3[ts3.length-1].date <= ts3[ts3.length-2].date) {
            console.log("This should never happen. Dates should be strictly increasing");
            debugger;
        }
    }
    return ts3;
}

function addIrregularTimeSeriesAndInterpolate(ts1, ts2) {
    var ts3 = [];
    var prevTs1 = 0;
    var prevTs2 = 0;
    var currPrice = 0;
    var n1 = ts1.length;
    var n2 = ts2.length;
    var i1 = 0, i2 = 0;
    while (i1 < n1 || i2 < n2) {
        if (i1 === n1) {
            ts1.push({ date: ts2[i2].date, price: 0 }); i1++; n1++;
            ts3.push(ts2[i2++]);
        } else if (i2 === n2) {
            ts2.push({ date: ts1[i1].date, price: 0 }); i2++; n2++;
            ts3.push(ts1[i1++]);
        } else if (ts1[i1].date == null || ts2[i2].date == null) {
            debugger;
        } else if (ts1[i1].date < ts2[i2].date) {
            var newTs1 = ts1[i1++];
            currPrice = round3dp(currPrice + (newTs1.price - prevTs1));
            ts2.splice(i2++, 0, { date: newTs1.date, price: prevTs2 }); n2++;
            ts3.push({ date: newTs1.date, price: currPrice });
            prevTs1 = newTs1.price;
        } else if (ts2[i2].date < ts1[i1].date) {
            var newTs2 = ts2[i2++];
            currPrice = round3dp(currPrice + (newTs2.price - prevTs2));
            ts1.splice(i1++, 0, { date: newTs2.date, price: prevTs1 }); n1++;
            ts3.push({ date: newTs2.date, price: currPrice });
            prevTs2 = newTs2.price;
        } else if (ts1[i1].date.getTime() === ts2[i2].date.getTime()) {
            // dates equal
            var newTs1 = ts1[i1++];
            var newTs2 = ts2[i2++];
            var priceIncrease = round3dp((newTs1.price - prevTs1) + (newTs2.price - prevTs2));
            currPrice = round3dp(currPrice + priceIncrease);
            if (currPrice < 0) {
                console.log("Negative price shouldn't be possible");
                debugger
            }
            ts3.push({ date: newTs1.date, price: currPrice });
            prevTs1 = newTs1.price;
            prevTs2 = newTs2.price;
        } else {
            console.log("This should never happen");
            debugger;
        }
        if (ts3.length >= 2 && ts3[ts3.length-1].date <= ts3[ts3.length-2].date) {
            console.log("This should never happen. Dates should be strictly increasing");
            debugger;
        }
    }
    
    if (!(ts1.length === ts2.length && ts2.length === ts3.length)) {
        console.log("This shouldn't happen. All three time series should be the same length");
        debugger;
    }
    
    return ts3;
}

function truncateIrregularTimeSeries(ts, extent) {
    var start = extent[0];
    var end = extent[1];
    var n = ts.length;
    var startPrice = 0;
    var startPrice0 = 0
    var startIndex = 0;
    var endPrice = 0;
    var endPrice0 = 0;
    var endIndex = 0;
    for (var i = 0; i < n; i++) {
        if (ts[i].date <= start) {
            endPrice = startPrice = ts[i].price;
            if (ts[i].price0 !== undefined) {
                endPrice0 = startPrice0 = ts[i].price0;
            }
            endIndex = startIndex = i + 1;
        } else {
            if (ts[i].date >= end) {
                break;
            }
            endPrice = ts[i].price;
            if (ts[i].price0 !== undefined) {
                endPrice0 = ts[i].price0;
            }
            endIndex = i + 1;
        }
    }
    return [{ date: start, price: startPrice, price0: startPrice0 }].concat(
        ts.slice(startIndex, endIndex),
        [{ date: end, price: endPrice, price0: endPrice0 }]
    );
}